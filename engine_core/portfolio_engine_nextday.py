import pandas as pd
import numpy as np
import logging
import os
from engine_core.db import fetch_df, get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INITIAL_CAPITAL = 100000.0

import argparse

def run_portfolio_simulation_nextday(start_date=None, end_date=None, tx_cost=0.004, output_prefix="nextday_"):
    """
    Realistic portfolio simulation where:
    - Signals are generated at EOD (using close price, regime, scores)
    - Trades are EXECUTED at next day's OPEN price
    This eliminates same-day close execution bias.
    """
    logger.info(f"Starting NEXT-DAY Execution Portfolio Simulation ({start_date or 'BEGIN'} to {end_date or 'END'})")
    logger.info(f"Transaction Cost: {tx_cost*100:.2f}% | Execution: NEXT DAY OPEN")
    
    conn = get_connection()
    
    # 1. Fetch market regime history
    logger.info("Loading market regime history...")
    regime_df = fetch_df("SELECT date, classification FROM market_regime WHERE classification IS NOT NULL ORDER BY date")
    
    if start_date:
        regime_df = regime_df[regime_df['date'] >= pd.to_datetime(start_date).date()]
    if end_date:
         regime_df = regime_df[regime_df['date'] <= pd.to_datetime(end_date).date()]
         
    regime_dict = dict(zip(regime_df['date'], regime_df['classification']))
    dates = sorted(list(regime_df['date']))
    
    if not dates:
        logger.error("No dates found matching criteria!")
        conn.close()
        return
        
    # 2. Fetch stock scores
    logger.info("Loading stock scores...")
    scores_df = fetch_df("SELECT date, symbol, total_score FROM stock_scores WHERE total_score IS NOT NULL")
    scores_df["date"] = pd.to_datetime(scores_df["date"], errors="coerce").dt.date
    scores_df["total_score"] = pd.to_numeric(scores_df["total_score"], errors="coerce")

    # 3. Fetch pricing — need BOTH close (for signals) and open (for execution)
    logger.info("Loading price data (close + open)...")
    prices_df = fetch_df("SELECT date, symbol, open, close FROM daily_prices")
    prices_df["date"] = pd.to_datetime(prices_df["date"], errors="coerce").dt.date
    prices_df["open"] = pd.to_numeric(prices_df["open"], errors="coerce")
    prices_df["close"] = pd.to_numeric(prices_df["close"], errors="coerce")
    conn.close()
    
    logger.info("Pre-processing data arrays for fast simulation...")
    
    # Close prices for signal evaluation and EOD equity
    prices_close_nested = prices_df.groupby('date').apply(lambda x: dict(zip(x.symbol, x.close))).to_dict()
    # Open prices for next-day trade execution
    prices_open_nested = prices_df.groupby('date').apply(lambda x: dict(zip(x.symbol, x['open']))).to_dict()
    scores_nested = scores_df.groupby('date').apply(lambda x: dict(zip(x.symbol, x.total_score))).to_dict()
    
    capital = INITIAL_CAPITAL
    positions = {}  # symbol -> {'shares': int, 'entry_price': float, 'highest_price': float, 'entry_date': date}
    trade_log = []
    equity_curve = []
    
    # Pending orders generated at EOD, executed at next day's open
    pending_exits = []   # list of (symbol, reason)
    pending_entries = [] # list of symbol
    
    logger.info(f"Running day-by-day simulation over {len(dates)} days...")
    
    for i, current_date in enumerate(dates):
        regime = regime_dict.get(current_date, 'NEUTRAL')
        
        today_close = prices_close_nested.get(current_date, {})
        today_open = prices_open_nested.get(current_date, {})
        today_scores = scores_nested.get(current_date, {})
        
        if not today_close:
            continue
            
        # ============================================================
        # PHASE 1: EXECUTE PENDING ORDERS from yesterday's signals
        # Use TODAY's OPEN price for execution
        # ============================================================
        
        # Execute pending exits
        for sym, reason in pending_exits:
            if sym in positions:
                exec_price = today_open.get(sym)
                if exec_price is None or exec_price <= 0:
                    exec_price = today_close.get(sym)  # fallback if no open
                if exec_price is None:
                    continue
                    
                pos_data = positions.pop(sym)
                shares = pos_data['shares']
                
                gross_proceeds = shares * exec_price
                cost = gross_proceeds * tx_cost
                net_proceeds = gross_proceeds - cost
                
                pnl = net_proceeds - (shares * pos_data['entry_price'])
                capital += net_proceeds
                
                trade_log.append({
                    'symbol': sym,
                    'entry_date': pos_data['entry_date'],
                    'exit_date': current_date,
                    'entry_price': pos_data['entry_price'],
                    'exit_price': exec_price,
                    'shares': shares,
                    'pnl': pnl,
                    'exit_reason': reason,
                    'execution': 'NEXT_DAY_OPEN'
                })
        
        # Execute pending entries
        for sym in pending_entries:
            if sym in positions:
                continue  # Already holding
            if len(positions) >= 10:
                break  # Full
                
            buy_price = today_open.get(sym)
            if buy_price is None or buy_price <= 0:
                buy_price = today_close.get(sym)  # fallback
            if buy_price is None or buy_price <= 0 or capital <= 0:
                continue
                
            # Size based on current equity
            current_equity = capital + sum([
                pos_data['shares'] * today_close.get(s, pos_data['entry_price']) 
                for s, pos_data in positions.items()
            ])
            allocation_per_slot = current_equity * 0.10
            
            invest_amount = min(allocation_per_slot, capital)
            post_fees_amount = invest_amount / (1 + tx_cost)
            shares = int(post_fees_amount // buy_price)
            
            cost = (shares * buy_price) * (1 + tx_cost)
            if shares > 0 and capital >= cost:
                capital -= cost
                positions[sym] = {
                    'shares': shares,
                    'entry_price': buy_price,
                    'highest_price': buy_price,
                    'entry_date': current_date
                }
        
        # Clear pending orders
        pending_exits = []
        pending_entries = []
        
        # ============================================================
        # PHASE 2: GENERATE SIGNALS for tomorrow using TODAY's CLOSE
        # ============================================================
        
        # Evaluate exits based on EOD data
        for sym, pos_data in positions.items():
            current_price = today_close.get(sym)
            if current_price is None:
                continue
                
            # Update trailing stop high water mark
            if current_price > pos_data['highest_price']:
                pos_data['highest_price'] = current_price
                
            current_score = today_scores.get(sym, 0)
            
            exit_reason = None
            if regime == 'BEAR':
                exit_reason = 'REGIME_BEAR'
            elif current_score <= 2:
                exit_reason = 'SCORE_LOW'
            elif current_price <= pos_data['highest_price'] * 0.8:
                exit_reason = 'TRAILING_STOP_20'
                
            if exit_reason:
                pending_exits.append((sym, exit_reason))
                
        # Evaluate entries based on EOD data
        if regime == 'BULL' and (len(positions) - len(pending_exits)) < 10:
            slots_available = 10 - (len(positions) - len(pending_exits))
            
            eligible_symbols = [
                s for s, score in today_scores.items() 
                if score >= 4 and s not in positions and s in today_close
            ]
            
            if eligible_symbols:
                eligible_symbols.sort(key=lambda s: today_scores[s], reverse=True)
                pending_entries = eligible_symbols[:slots_available]
                
        # ============================================================
        # PHASE 3: RECORD EOD EQUITY
        # ============================================================
        eod_equity = capital + sum([
            pos_data['shares'] * today_close.get(s, pos_data['entry_price']) 
            for s, pos_data in positions.items()
        ])
        equity_curve.append({
            'date': current_date, 
            'equity': eod_equity,
            'cash': capital,
            'open_positions': len(positions)
        })

    logger.info("Simulation complete. Writing state...")
    os.makedirs('outputs', exist_ok=True)
    
    trades_df = pd.DataFrame(trade_log)
    trades_df.to_csv(f'outputs/{output_prefix}trade_log.csv', index=False)
    
    equity_df = pd.DataFrame(equity_curve)
    equity_df.to_csv(f'outputs/{output_prefix}equity_curve.csv', index=False)
    
    logger.info(f"Total trades: {len(trades_df)}")
    if equity_curve:
        final_eq = equity_curve[-1]['equity']
        cagr = ((final_eq / INITIAL_CAPITAL) ** (252.0 / len(dates))) - 1.0
        logger.info(f"Final Equity: ₹{final_eq:,.2f}")
        logger.info(f"Approx CAGR: {cagr*100:.2f}%")

    # Compare with original
    logger.info("")
    logger.info("=" * 60)
    logger.info("COMPARISON: Original (same-day close) vs Next-Day Open")
    logger.info("=" * 60)
    logger.info("Original: Final Equity ₹9,750,142 | CAGR ~29.04%")
    logger.info(f"Next-Day: Final Equity ₹{final_eq:,.2f} | CAGR {cagr*100:.2f}%")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Next-Day Execution Portfolio Backtest")
    parser.add_argument('--start-date', type=str, default=None)
    parser.add_argument('--end-date', type=str, default=None)
    parser.add_argument('--tx-cost', type=float, default=0.004)
    parser.add_argument('--output-prefix', type=str, default="nextday_")
    
    args = parser.parse_args()
    
    run_portfolio_simulation_nextday(
        start_date=args.start_date,
        end_date=args.end_date,
        tx_cost=args.tx_cost,
        output_prefix=args.output_prefix
    )


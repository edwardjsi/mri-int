import pandas as pd
import numpy as np
import logging
import os
from src.db import get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INITIAL_CAPITAL = 100000.0
TRANSACTION_COST = 0.004 # 0.4% total cost logic

import argparse

def run_portfolio_simulation(start_date=None, end_date=None, tx_cost=0.004, output_prefix=""):
    logger.info(f"Starting Portfolio Simulation Engine ({start_date or 'BEGIN'} to {end_date or 'END'})")
    logger.info(f"Transaction Cost: {tx_cost*100:.2f}% | Output Prefix: '{output_prefix}'")
    
    conn = get_connection()
    
    # 1. Fetch entire market regime history
    logger.info("Loading market regime history...")
    regime_df = pd.read_sql("SELECT date, classification FROM market_regime WHERE classification IS NOT NULL ORDER BY date", conn)
    
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
    scores_query = "SELECT date, symbol, total_score FROM stock_scores WHERE total_score IS NOT NULL"
    scores_df = pd.read_sql(scores_query, conn)
    
    # 3. Fetch pricing
    logger.info("Loading price data...")
    prices_query = "SELECT date, symbol, close FROM daily_prices"
    prices_df = pd.read_sql(prices_query, conn)
    
    conn.close()
    
    logger.info("Pre-processing data arrays for fast simulation...")
    # Map data for fast daily traversal
    # To save memory and time, we create nested dicts: date -> symbol -> value
    # E.g., price_map[date][symbol] = close
    
    logger.info("Building nested dictionaries...")
    # This acts as O(1) daily lookups
    prices_nested = prices_df.groupby('date').apply(lambda x: dict(zip(x.symbol, x.close))).to_dict()
    scores_nested = scores_df.groupby('date').apply(lambda x: dict(zip(x.symbol, x.total_score))).to_dict()
    
    capital = INITIAL_CAPITAL
    positions = {} # dict of symbol -> {'shares': int, 'entry_price': float, 'highest_price': float, 'entry_date': date}
    trade_log = []
    equity_curve = []
    
    logger.info(f"Running day-by-day simulation over {len(dates)} days...")
    
    for current_date in dates:
        regime = regime_dict.get(current_date, 'NEUTRAL')
        
        today_prices = prices_nested.get(current_date, {})
        today_scores = scores_nested.get(current_date, {})
        
        if not today_prices:
            # Market holiday or no data
            continue
            
        # 1. EVALUATE EXITS
        symbols_to_exit = []
        for sym, pos_data in positions.items():
            current_price = today_prices.get(sym)
            if current_price is None:
                continue # No price today, hold
                
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
                symbols_to_exit.append((sym, current_price, exit_reason))
                
        # Process Exits
        for sym, exit_price, reason in symbols_to_exit:
            pos_data = positions.pop(sym)
            shares = pos_data['shares']
            
            gross_proceeds = shares * exit_price
            cost = gross_proceeds * tx_cost
            net_proceeds = gross_proceeds - cost
            
            pnl = net_proceeds - (shares * pos_data['entry_price'])
            capital += net_proceeds
            
            trade_log.append({
                'symbol': sym,
                'entry_date': pos_data['entry_date'],
                'exit_date': current_date,
                'entry_price': pos_data['entry_price'],
                'exit_price': exit_price,
                'shares': shares,
                'pnl': pnl,
                'exit_reason': reason
            })
            
        # 2. EVALUATE ENTRIES
        # Entry requires BULL regime, Score >= 4, and equal weight 10% positions.
        if regime == 'BULL' and len(positions) < 10:
            slots_available = 10 - len(positions)
            
            # Find eligible symbols
            eligible_symbols = [s for s, score in today_scores.items() if score >= 4 and s not in positions and s in today_prices]
            
            if eligible_symbols:
                # Sort eligible by score descending (using relative strength as tie-breaker is too complex for this prototype step, so we just sort by score)
                eligible_symbols.sort(key=lambda s: today_scores[s], reverse=True)
                to_buy_symbols = eligible_symbols[:slots_available]
                
                # Calculate current equity to determine position sizing
                current_equity = capital + sum([pos_data['shares'] * today_prices.get(s, pos_data['entry_price']) for s, pos_data in positions.items()])
                allocation_per_slot = current_equity * 0.10
                
                for sym in to_buy_symbols:
                    buy_price = today_prices.get(sym)
                    if buy_price and buy_price > 0 and capital > 0:
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
                            
        # 3. RECORD EOD EQUITY
        eod_equity = capital + sum([pos_data['shares'] * today_prices.get(s, pos_data['entry_price']) for s, pos_data in positions.items()])
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Portfolio Backtest Simulation")
    parser.add_argument('--start-date', type=str, default=None, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None, help='End date (YYYY-MM-DD)')
    parser.add_argument('--tx-cost', type=float, default=0.004, help='Transaction cost (e.g., 0.004 for 0.4%)')
    parser.add_argument('--output-prefix', type=str, default="", help='Prefix for output CSV files')
    
    args = parser.parse_args()
    
    run_portfolio_simulation(
        start_date=args.start_date,
        end_date=args.end_date,
        tx_cost=args.tx_cost,
        output_prefix=args.output_prefix
    )

import pandas as pd
import numpy as np
import os
from collections import defaultdict
import time

def simulate_mtm_portfolio(scenarios_df, price_data_dict, dates, variant_name, sort_keys, sort_ascending):
    # Core Proxy
    df = scenarios_df[
        (scenarios_df['execution_variant'] == 'DAILY-BAR OPTIMISTIC EXECUTION PROXY') &
        (scenarios_df['slippage_buffer_assumption'] == '0.00%') &
        (scenarios_df['tp_variant'] == '+2R_OR_6%')
    ].copy()
    
    capital = 1000000.0
    cash = capital
    portfolio_equity = capital
    
    open_positions = {}
    
    entries_by_date = defaultdict(list)
    for idx, row in df.iterrows():
        entries_by_date[row['entry_date']].append(row)
        
    exits_by_date = defaultdict(list)
    for idx, row in df.iterrows():
        exits_by_date[row['exit_date']].append(row)
        
    equity_curve = []
    skipped_trades = []
    accepted_trades = []
    
    for current_date in dates:
        # 1. Determine currently open positions (carried over from yesterday)
        # 2. Obtain each position's current close & 3. Calculate market value
        market_value_of_open = 0.0
        cost_basis_of_open = 0.0
        for trade_id, p in list(open_positions.items()):
            sym = p['symbol']
            sym_df = price_data_dict.get(sym)
            if sym_df is not None and current_date in sym_df.index:
                current_close = sym_df.loc[current_date, 'close']
                p['current_close'] = current_close # Update internal state
            else:
                current_close = p['current_close'] # fallback to last known if missing
            
            p_mv = p['shares'] * current_close
            market_value_of_open += p_mv
            cost_basis_of_open += p['position_cost']
            
        # 4. Calculate portfolio equity (BEFORE EXITS/ENTRIES today)
        portfolio_equity = cash + market_value_of_open
        
        # 6. Process exits (if any trigger today based on trade management)
        # The exit_date in our scenarios_df is the date the stop was hit.
        today_exits = [t for t in list(open_positions.values()) if t['exit_date'] == current_date]
        for t in today_exits:
            exit_proceeds = t['shares'] * t['exit_price']
            # 7. Release exit cash
            cash += exit_proceeds
            del open_positions[t['trade_id']]
            accepted_trades.append({**t, 'realized_proceeds': exit_proceeds})
            # Adjust MV and Cost basis for the remaining day's stats
            market_value_of_open -= (t['shares'] * t['current_close'])
            cost_basis_of_open -= t['position_cost']
            
        # 8. Recalculate available capital/equity
        portfolio_equity = cash + market_value_of_open
        
        # 9. Process new entries
        today_entries = entries_by_date.get(current_date, [])
        if today_entries:
            candidates = pd.DataFrame(today_entries)
            candidates = candidates.sort_values(by=sort_keys, ascending=sort_ascending)
            
            for _, row in candidates.iterrows():
                risk_budget = portfolio_equity * 0.0075
                risk_per_share = row['risk_per_share']
                
                shares = np.floor(risk_budget / risk_per_share) if risk_per_share > 0 else 0
                position_cost = shares * row['entry_price']
                
                if shares < 1:
                    skipped_trades.append({'trade_id': row['trade_id'], 'date': current_date, 'reason': 'Shares < 1'})
                    continue
                    
                if position_cost > cash:
                    skipped_trades.append({'trade_id': row['trade_id'], 'date': current_date, 'reason': 'Insufficient Cash'})
                    continue
                    
                # Allocate accepted positions
                cash -= position_cost
                open_positions[row['trade_id']] = {
                    'trade_id': row['trade_id'],
                    'symbol': row['symbol'],
                    'entry_date': row['entry_date'],
                    'entry_price': row['entry_price'],
                    'exit_date': row['exit_date'],
                    'exit_price': row['exit_price'],
                    'shares': shares,
                    'position_cost': position_cost,
                    'current_close': row['entry_price'], # Starts at entry price
                    'net_R': row['net_R']
                }
                market_value_of_open += position_cost
                cost_basis_of_open += position_cost
                
        # Recalc after entries
        portfolio_equity = cash + market_value_of_open
        
        # 10. Record end-of-day portfolio state
        equity_curve.append({
            'date': current_date,
            'opening_cash': cash, # Approximation, actual opening was before exits
            'closing_cash': cash,
            'market_value': market_value_of_open,
            'invested_cost': cost_basis_of_open,
            'total_equity': portfolio_equity,
            'open_position_count': len(open_positions)
        })
        
    eq_df = pd.DataFrame(equity_curve)
    
    # 5. Calculate drawdown from historical peak (daily MTM)
    eq_df['peak_equity'] = eq_df['total_equity'].cummax()
    eq_df['drawdown'] = (eq_df['total_equity'] - eq_df['peak_equity']) / eq_df['peak_equity']
    eq_df['daily_return'] = eq_df['total_equity'].pct_change()
    
    eq_df['market_exposure'] = eq_df['market_value'] / eq_df['total_equity']
    eq_df['cost_basis_exposure'] = eq_df['invested_cost'] / eq_df['total_equity']
    eq_df['cash_percentage'] = eq_df['closing_cash'] / eq_df['total_equity']
    
    max_dd = eq_df['drawdown'].min()
    final_equity = eq_df['total_equity'].iloc[-1] if not eq_df.empty else capital
    total_return = (final_equity / capital) - 1
    
    days = (dates[-1] - dates[0]).days if len(dates) > 1 else 365
    cagr = ((final_equity / capital) ** (365.25 / days)) - 1 if days > 0 else 0
    
    accepted_df = pd.DataFrame(accepted_trades)
    
    # Close out any remaining open positions at the end of backtest to record them properly
    final_date = dates[-1] if dates else pd.Timestamp.now()
    unrealized_pnl = 0.0
    for trade_id, p in open_positions.items():
        mv = p['shares'] * p['current_close']
        unrealized_pnl += (mv - p['position_cost'])
        
    wins = len(accepted_df[accepted_df['net_R'] > 0]) if not accepted_df.empty else 0
    losses = len(accepted_df[accepted_df['net_R'] <= 0]) if not accepted_df.empty else 0
    win_rate = wins / len(accepted_df) if not accepted_df.empty else 0
    gross_profits = accepted_df[accepted_df['net_R'] > 0]['net_R'].sum() if not accepted_df.empty else 0
    gross_losses = abs(accepted_df[accepted_df['net_R'] <= 0]['net_R'].sum()) if not accepted_df.empty else 0
    pf = gross_profits / gross_losses if gross_losses > 0 else float('inf')
    
    print(f"\n--- Portfolio Variant: {variant_name} (MTM) ---")
    print(f"Total Accepted Trades: {len(accepted_trades)}")
    print(f"Final Equity: {final_equity:,.2f}")
    print(f"CAGR: {cagr*100:.2f}%")
    print(f"Max DD: {max_dd*100:.2f}%")
    print(f"Avg Market Exposure: {eq_df['market_exposure'].mean()*100:.2f}%")
    print(f"Avg Cost Exposure: {eq_df['cost_basis_exposure'].mean()*100:.2f}%")
    print(f"Open Positions at End: {len(open_positions)} (Unrealized P&L: {unrealized_pnl:,.2f})")
    
    return {
        'Variant': variant_name,
        'Final Equity': final_equity,
        'CAGR': cagr,
        'Max DD': max_dd,
        'Avg Market Exposure': eq_df['market_exposure'].mean(),
        'Win Rate': win_rate,
        'Profit Factor': pf,
        'Trades': len(accepted_trades)
    }

def main():
    print("Loading datasets for MTM Portfolio Simulation...")
    df = pd.read_pickle('scratch/minervini_base.pkl') if os.path.exists('scratch/minervini_base.pkl') else pd.read_csv('/home/immanuels/Desktop/mri-int/backups/20260304/daily_prices.csv')
    df['date'] = pd.to_datetime(df['date'])
    
    # We only need dates that are on or after our first breakout
    scenarios = pd.read_pickle('scratch/validation_scenarios.pkl')
    min_date = scenarios['entry_date'].min()
    df = df[df['date'] >= min_date].copy()
    
    print("Indexing price data...")
    grouped = df.groupby('symbol')
    price_data = {}
    for sym, group in grouped:
        price_data[sym] = group.set_index('date').sort_index()
        
    dates = pd.Series(df['date'].unique()).sort_values().tolist()
    
    print("Simulating Variant A...")
    va = simulate_mtm_portfolio(scenarios, price_data, dates, "Variant A (Contraction->VDU->Symbol)", ['contraction_count', 'vdu_count', 'symbol'], [False, False, True])
    
    print("Simulating Variant B...")
    vb = simulate_mtm_portfolio(scenarios, price_data, dates, "Variant B (Symbol Only)", ['symbol'], [True])
    
    results = [va, vb]
    pd.DataFrame(results).to_pickle('scratch/validation_mtm_results.pkl')

if __name__ == '__main__':
    main()

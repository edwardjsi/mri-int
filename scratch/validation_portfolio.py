import pandas as pd
import numpy as np
import os
from collections import defaultdict

def simulate_portfolio(scenarios_df, variant_name, sort_keys, sort_ascending):
    # We will simulate the CORE proxy: Optimistic, 0% Slippage, +2R OR +6% tp variant
    df = scenarios_df[
        (scenarios_df['execution_variant'] == 'DAILY-BAR OPTIMISTIC EXECUTION PROXY') &
        (scenarios_df['slippage_buffer_assumption'] == '0.00%') &
        (scenarios_df['tp_variant'] == '+2R_OR_6%')
    ].copy()
    
    # We need a chronological simulation
    # Events: Entries (breakout_date), Exits (exit_date)
    # Since we use Next Day open for exits usually, the exit_date is the day the stop was hit.
    # We realize cash AT THE END of exit_date, so it is available ON THE NEXT TRADING DAY.
    
    # Let's get all unique trading dates from the universe
    dates = pd.Series(pd.concat([df['entry_date'], df['exit_date']]).unique()).sort_values().dropna().tolist()
    
    capital = 1000000.0
    cash = capital
    portfolio_equity = capital
    
    open_positions = {} # trade_id -> dict of details
    
    # Pre-group entries by date
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
        # 1. Process exits of existing positions
        today_exits = [t for t in list(open_positions.values()) if t['exit_date'] == current_date]
        for t in today_exits:
            exit_proceeds = t['shares'] * t['exit_price']
            # 2. Realize cash from exits
            cash += exit_proceeds
            del open_positions[t['trade_id']]
            accepted_trades.append({**t, 'realized_proceeds': exit_proceeds})
            
        # 3. Calculate current portfolio equity
        # For simplicity of daily closing equity, we value open positions at entry price if we don't load the full DB
        # To be completely accurate, we should load full DB, but since we just need equity for risk allocation:
        # We will use the running cash + (shares * current_price). 
        # But wait, without full price db, we don't have current_price.
        # However, we DO have the entry price and we can assume equity = cash + sum(position_cost)
        # This is a simplification (using cost basis for risk allocation instead of mark-to-market).
        # Let's use cost basis for risk allocation to keep it fast and deterministic.
        portfolio_value_at_cost = sum([p['position_cost'] for p in open_positions.values()])
        portfolio_equity = cash + portfolio_value_at_cost
        
        # 4. Identify eligible new entries
        today_entries = entries_by_date.get(current_date, [])
        if today_entries:
            # 7. Rank simultaneous candidates
            candidates = pd.DataFrame(today_entries)
            candidates = candidates.sort_values(by=sort_keys, ascending=sort_ascending)
            
            for _, row in candidates.iterrows():
                # 5. Calculate position sizes using current equity
                risk_budget = portfolio_equity * 0.0075
                risk_per_share = row['risk_per_share']
                
                shares = np.floor(risk_budget / risk_per_share) if risk_per_share > 0 else 0
                position_cost = shares * row['entry_price']
                
                if shares < 1:
                    skipped_trades.append({'trade_id': row['trade_id'], 'date': current_date, 'reason': 'Shares < 1'})
                    continue
                    
                # 6. Apply cash constraint
                if position_cost > cash:
                    skipped_trades.append({'trade_id': row['trade_id'], 'date': current_date, 'reason': 'Insufficient Cash'})
                    continue
                    
                # 8. Allocate accepted positions
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
                    'net_R': row['net_R']
                }
                
        # 10. Mark end-of-day portfolio equity
        current_portfolio_value_at_cost = sum([p['position_cost'] for p in open_positions.values()])
        equity_curve.append({
            'date': current_date,
            'cash': cash,
            'invested': current_portfolio_value_at_cost,
            'equity': cash + current_portfolio_value_at_cost,
            'open_positions': len(open_positions)
        })
        
    eq_df = pd.DataFrame(equity_curve)
    
    # Calculate portfolio stats
    final_equity = eq_df['equity'].iloc[-1] if not eq_df.empty else capital
    total_return = (final_equity / capital) - 1
    
    # CAGR (approx based on days)
    days = (dates[-1] - dates[0]).days if len(dates) > 1 else 365
    cagr = ((final_equity / capital) ** (365.25 / days)) - 1 if days > 0 else 0
    
    # Max Drawdown (using equity curve)
    eq_df['peak'] = eq_df['equity'].cummax()
    eq_df['drawdown'] = (eq_df['equity'] - eq_df['peak']) / eq_df['peak']
    max_dd = eq_df['drawdown'].min()
    
    accepted_df = pd.DataFrame(accepted_trades)
    
    wins = len(accepted_df[accepted_df['net_R'] > 0]) if not accepted_df.empty else 0
    losses = len(accepted_df[accepted_df['net_R'] <= 0]) if not accepted_df.empty else 0
    win_rate = wins / len(accepted_df) if not accepted_df.empty else 0
    
    gross_profits = accepted_df[accepted_df['net_R'] > 0]['net_R'].sum() if not accepted_df.empty else 0
    gross_losses = abs(accepted_df[accepted_df['net_R'] <= 0]['net_R'].sum()) if not accepted_df.empty else 0
    pf = gross_profits / gross_losses if gross_losses > 0 else float('inf')
    
    avg_win = accepted_df[accepted_df['net_R'] > 0]['net_R'].mean() if wins > 0 else 0
    avg_loss = accepted_df[accepted_df['net_R'] <= 0]['net_R'].mean() if losses > 0 else 0
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
    
    print(f"\n--- Portfolio Variant: {variant_name} ---")
    print(f"Total Accepted Trades: {len(accepted_trades)}")
    print(f"Total Skipped Trades: {len(skipped_trades)}")
    print(f"Final Equity: {final_equity:,.2f}")
    print(f"Total Return: {total_return*100:.2f}%")
    print(f"CAGR: {cagr*100:.2f}%")
    print(f"Max Drawdown: {max_dd*100:.2f}%")
    print(f"Win Rate: {win_rate*100:.2f}%")
    print(f"Profit Factor: {pf:.2f}")
    print(f"Expectancy: {expectancy:.2f}R")
    print(f"Max Concurrent Positions: {eq_df['open_positions'].max()}")
    print(f"Average Exposure (Invested/Equity): {(eq_df['invested'] / eq_df['equity']).mean()*100:.2f}%")
    
    return {
        'Variant': variant_name,
        'Final Equity': final_equity,
        'CAGR': cagr,
        'Max DD': max_dd,
        'Win Rate': win_rate,
        'Expectancy': expectancy,
        'Trades': len(accepted_trades)
    }

def main():
    if not os.path.exists('scratch/validation_scenarios.pkl'):
        print("Waiting for validation_scenarios.pkl...")
        return
        
    scenarios = pd.read_pickle('scratch/validation_scenarios.pkl')
    
    # Variant A: Contractions DESC, VDU DESC, Symbol ASC
    simulate_portfolio(scenarios, "Variant A (Contraction->VDU->Symbol)", ['contraction_count', 'vdu_count', 'symbol'], [False, False, True])
    
    # Variant B: Symbol ASC Only
    simulate_portfolio(scenarios, "Variant B (Symbol Only)", ['symbol'], [True])

if __name__ == '__main__':
    main()

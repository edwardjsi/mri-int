import pandas as pd
import numpy as np
import os
from collections import defaultdict
import time

def simulate_mtm_portfolio(scenarios_df, price_data_dict, dates, variant_name, sort_keys, sort_ascending):
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
        
    equity_curve = []
    skipped_trades = []
    accepted_trades = []
    
    for current_date in dates:
        market_value_of_open = 0.0
        cost_basis_of_open = 0.0
        for trade_id, p in list(open_positions.items()):
            sym = p['symbol']
            sym_df = price_data_dict.get(sym)
            if sym_df is not None and current_date in sym_df.index:
                current_close = sym_df.loc[current_date, 'close']
                p['current_close'] = current_close
            else:
                current_close = p['current_close']
            
            p_mv = p['shares'] * current_close
            market_value_of_open += p_mv
            cost_basis_of_open += p['position_cost']
            
        portfolio_equity = cash + market_value_of_open
        
        # BUG FIX: Use <= current_date to catch missed same-day exits
        today_exits = [t for t in list(open_positions.values()) if t['exit_date'] <= current_date]
        for t in today_exits:
            exit_proceeds = t['shares'] * t['exit_price']
            cash += exit_proceeds
            del open_positions[t['trade_id']]
            accepted_trades.append({**t, 'realized_proceeds': exit_proceeds, 'actual_exit_processed_date': current_date})
            
            # Since it might be exiting at a different price than today's close, just subtract what was added
            market_value_of_open -= (t['shares'] * t['current_close'])
            cost_basis_of_open -= t['position_cost']
            
        portfolio_equity = cash + market_value_of_open
        
        today_entries = entries_by_date.get(current_date, [])
        if today_entries:
            candidates = pd.DataFrame(today_entries).sort_values(by=sort_keys, ascending=sort_ascending)
            
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
                    'current_close': row['entry_price'],
                    'net_R': row['net_R']
                }
                market_value_of_open += position_cost
                cost_basis_of_open += position_cost
                
                # If this trade exits TODAY, it will be processed on the NEXT trading day.
                # This perfectly mimics T+1 cash settlement.
                
        portfolio_equity = cash + market_value_of_open
        
        equity_curve.append({
            'date': current_date,
            'opening_cash': cash,
            'closing_cash': cash,
            'market_value': market_value_of_open,
            'invested_cost': cost_basis_of_open,
            'total_equity': portfolio_equity,
            'open_position_count': len(open_positions)
        })
        
    eq_df = pd.DataFrame(equity_curve)
    eq_df['peak_equity'] = eq_df['total_equity'].cummax()
    eq_df['drawdown'] = (eq_df['total_equity'] - eq_df['peak_equity']) / eq_df['peak_equity']
    
    eq_df['market_exposure'] = eq_df['market_value'] / eq_df['total_equity']
    eq_df['cost_basis_exposure'] = eq_df['invested_cost'] / eq_df['total_equity']
    
    max_dd = eq_df['drawdown'].min()
    final_equity = eq_df['total_equity'].iloc[-1] if not eq_df.empty else capital
    cagr = ((final_equity / capital) ** (365.25 / (dates[-1] - dates[0]).days)) - 1 if len(dates) > 1 else 0
    
    print(f"\n--- {variant_name} (FIXED MTM) ---")
    print(f"Final Equity: {final_equity:,.2f}")
    print(f"CAGR: {cagr*100:.2f}%")
    print(f"Max DD: {max_dd*100:.2f}%")
    print(f"Avg Market Exposure: {eq_df['market_exposure'].mean()*100:.2f}%")
    print(f"Avg Cost Exposure: {eq_df['cost_basis_exposure'].mean()*100:.2f}%")

def main():
    df = pd.read_pickle('scratch/minervini_base.pkl')
    df['date'] = pd.to_datetime(df['date'])
    scenarios = pd.read_pickle('scratch/validation_scenarios.pkl')
    df = df[df['date'] >= scenarios['entry_date'].min()].copy()
    
    price_data = {}
    for sym, group in df.groupby('symbol'):
        price_data[sym] = group.set_index('date').sort_index()
        
    dates = pd.Series(df['date'].unique()).sort_values().tolist()
    
    simulate_mtm_portfolio(scenarios, price_data, dates, "Variant A (Contraction->VDU->Symbol)", ['contraction_count', 'vdu_count', 'symbol'], [False, False, True])
    simulate_mtm_portfolio(scenarios, price_data, dates, "Variant B (Symbol Only)", ['symbol'], [True])

if __name__ == '__main__':
    main()

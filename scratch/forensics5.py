import pandas as pd
import numpy as np

def simulate_mtm_portfolio(scenarios_df, price_data_dict, dates):
    df = scenarios_df[
        (scenarios_df['execution_variant'] == 'DAILY-BAR OPTIMISTIC EXECUTION PROXY') &
        (scenarios_df['slippage_buffer_assumption'] == '0.00%') &
        (scenarios_df['tp_variant'] == '+2R_OR_6%')
    ].copy()
    
    capital = 1000000.0
    cash = capital
    portfolio_equity = capital
    open_positions = {}
    
    entries_by_date = {}
    for idx, row in df.iterrows():
        entries_by_date.setdefault(row['entry_date'], []).append(row)
        
    for current_date in dates:
        market_value_of_open = 0.0
        for trade_id, p in list(open_positions.items()):
            sym = p['symbol']
            sym_df = price_data_dict.get(sym)
            if sym_df is not None and current_date in sym_df.index:
                p['current_close'] = sym_df.loc[current_date, 'close']
            
            p_mv = p['shares'] * p['current_close']
            market_value_of_open += p_mv
            
        portfolio_equity = cash + market_value_of_open
        
        today_exits = [t for t in list(open_positions.values()) if t['exit_date'] == current_date]
        for t in today_exits:
            cash += t['shares'] * t['exit_price']
            del open_positions[t['trade_id']]
            market_value_of_open -= (t['shares'] * t['current_close'])
            
        portfolio_equity = cash + market_value_of_open
        
        today_entries = entries_by_date.get(current_date, [])
        if today_entries:
            candidates = pd.DataFrame(today_entries).sort_values(by=['contraction_count', 'vdu_count', 'symbol'], ascending=[False, False, True])
            
            for _, row in candidates.iterrows():
                risk_budget = portfolio_equity * 0.0075
                shares = np.floor(risk_budget / row['risk_per_share']) if row['risk_per_share'] > 0 else 0
                position_cost = shares * row['entry_price']
                
                if shares < 1 or position_cost > cash:
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
                    'current_close': row['entry_price']
                }
                market_value_of_open += position_cost
                
    for trade_id, p in open_positions.items():
        mv = p['shares'] * p['current_close']
        print(f"OPEN POSITION: {trade_id}")
        print(f"Symbol: {p['symbol']}")
        print(f"Entry Date: {p['entry_date'].date()}")
        print(f"Entry Price: {p['entry_price']}")
        print(f"Shares: {p['shares']}")
        print(f"Position Cost: {p['position_cost']}")
        print(f"Final Close: {p['current_close']}")
        print(f"Final Market Value: {mv}")
        print(f"Unrealized P&L: {mv - p['position_cost']}")

def main():
    df = pd.read_pickle('scratch/minervini_base.pkl')
    df['date'] = pd.to_datetime(df['date'])
    scenarios = pd.read_pickle('scratch/validation_scenarios.pkl')
    df = df[df['date'] >= scenarios['entry_date'].min()].copy()
    
    price_data = {}
    for sym, group in df.groupby('symbol'):
        price_data[sym] = group.set_index('date').sort_index()
        
    dates = pd.Series(df['date'].unique()).sort_values().tolist()
    simulate_mtm_portfolio(scenarios, price_data, dates)

if __name__ == '__main__':
    main()

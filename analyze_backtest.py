import os
import pandas as pd
import numpy as np

def calculate_metrics(df_subset):
    if len(df_subset) == 0:
        return {}
    
    wins = df_subset[df_subset['net_return'] > 0]
    losses = df_subset[df_subset['net_return'] <= 0]
    
    total_trades = len(df_subset)
    win_rate = len(wins) / total_trades if total_trades > 0 else 0
    avg_net_return = df_subset['net_return'].mean()
    
    sum_win_ret = wins['net_return'].sum()
    sum_loss_ret = abs(losses['net_return'].sum())
    profit_factor = sum_win_ret / sum_loss_ret if sum_loss_ret != 0 else float('inf')
    
    avg_mfe = df_subset['mfe'].mean()
    avg_mae = df_subset['mae'].mean()
    
    # Winner retention: What % of the max peak profit did we keep on winning trades?
    # (avoid div by zero by filtering out mfe=0, though for wins mfe > 0)
    valid_retention = wins[wins['mfe'] > 0]
    avg_winner_retention = (valid_retention['net_return'] / valid_retention['mfe']).mean() if len(valid_retention) > 0 else 0
    
    avg_post_exit_opp = df_subset['post_exit_max_60d'].mean()
    avg_duration = df_subset['duration'].mean()
    
    return {
        'Trades': total_trades,
        'Win Rate (%)': win_rate * 100,
        'Avg Return (%)': avg_net_return * 100,
        'Profit Factor': profit_factor,
        'Avg MFE (%)': avg_mfe * 100,
        'Avg MAE (%)': avg_mae * 100,
        'Winner Retention (%)': avg_winner_retention * 100,
        'Post-Exit Opp (%)': avg_post_exit_opp * 100,
        'Avg Duration': avg_duration
    }

def main():
    df = pd.read_csv('backtest_trades_v01.csv')
    df['signal_date'] = pd.to_datetime(df['signal_date'])
    
    # Sort dates to split
    unique_dates = np.sort(df['signal_date'].unique())
    n = len(unique_dates)
    train_end = unique_dates[int(n * 0.5)]
    val_end = unique_dates[int(n * 0.75)]
    
    df_train = df[df['signal_date'] <= train_end]
    df_val = df[(df['signal_date'] > train_end) & (df['signal_date'] <= val_end)]
    df_test = df[df['signal_date'] > val_end]
    
    splits = {
        'Training (First 50%)': df_train,
        'Validation (Next 25%)': df_val,
        'Test (Last 25%)': df_test,
        'Overall (100%)': df
    }
    
    strategies = df['strategy'].unique()
    
    with open('results.md', 'w') as f:
        f.write("# V0.1 Backtest Results\\n\\n")
        f.write(f"**Total Breakouts Analysed:** {len(df_train)/len(strategies):.0f} (Train), {len(df_val)/len(strategies):.0f} (Val), {len(df_test)/len(strategies):.0f} (Test)\\n\\n")
        
        for split_name, split_df in splits.items():
            f.write(f"## {split_name}\\n")
            
            results = []
            for strat in strategies:
                strat_df = split_df[split_df['strategy'] == strat]
                metrics = calculate_metrics(strat_df)
                if metrics:
                    metrics['Strategy'] = strat
                    results.append(metrics)
                    
            if not results:
                continue
                
            res_df = pd.DataFrame(results)
            # Reorder columns
            cols = ['Strategy', 'Trades', 'Win Rate (%)', 'Avg Return (%)', 'Profit Factor', 
                    'Winner Retention (%)', 'Post-Exit Opp (%)', 'Avg MFE (%)', 'Avg MAE (%)', 'Avg Duration']
            res_df = res_df[cols]
            
            # Sort by Avg Return for easy reading
            res_df = res_df.sort_values('Avg Return (%)', ascending=False)
            
            # Format numbers
            for col in res_df.columns:
                if col not in ['Strategy', 'Trades']:
                    res_df[col] = res_df[col].map('{:.2f}'.format)
            
            f.write(res_df.to_markdown(index=False))
            f.write("\\n\\n")

if __name__ == '__main__':
    main()

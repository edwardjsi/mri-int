import pandas as pd

def main():
    df = pd.read_pickle('scratch/minervini_base.pkl')
    axis = df[(df['symbol'] == 'AXISBANK') & (df['date'] >= '2000-08-15') & (df['date'] <= '2000-10-15')].copy()
    
    axis['prev_close'] = axis['close'].shift(1)
    axis['ret'] = axis['close'] / axis['prev_close'] - 1
    
    print("\n--- AXISBANK FORENSICS ---")
    for idx, row in axis.iterrows():
        print(f"{row['date'].date()} | Open: {row['open']:>8.4f} | High: {row['high']:>8.4f} | Low: {row['low']:>8.4f} | Close: {row['close']:>8.4f} | Vol: {row['volume']:>8.0f}")

    scenarios = pd.read_pickle('scratch/validation_scenarios.pkl')
    va_trades = scenarios[
        (scenarios['execution_variant'] == 'DAILY-BAR OPTIMISTIC EXECUTION PROXY') &
        (scenarios['slippage_buffer_assumption'] == '0.00%') &
        (scenarios['tp_variant'] == '+2R_OR_6%')
    ]
    t = va_trades[va_trades['trade_id'] == 'AXISBANK_20000831_Opt_S0_+2R_OR_6%'].iloc[0]
    print("\nTRADE DETAILS:")
    print(t)

if __name__ == '__main__':
    main()

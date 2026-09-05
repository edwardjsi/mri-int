import pandas as pd

def main():
    scenarios = pd.read_pickle('scratch/validation_scenarios.pkl')
    va_trades = scenarios[
        (scenarios['execution_variant'] == 'DAILY-BAR OPTIMISTIC EXECUTION PROXY') &
        (scenarios['slippage_buffer_assumption'] == '0.00%') &
        (scenarios['tp_variant'] == '+2R_OR_6%')
    ]
    df = pd.read_pickle('scratch/minervini_base.pkl')
    max_date = df['date'].max()
    
    open_trades = va_trades[va_trades['exit_date'] == max_date].copy()
    
    outlier = None
    max_ret = 0
    for idx, t in open_trades.iterrows():
        sym_df = df[df['symbol'] == t['symbol']].copy()
        final_close = sym_df.loc[sym_df['date'] == max_date, 'close'].values[0]
        
        ret = final_close / t['entry_price']
        if ret > max_ret:
            max_ret = ret
            outlier = t
            
    if outlier is not None:
        print(f"OUTLIER TRADE: {outlier['trade_id']}")
        print(f"Symbol: {outlier['symbol']}")
        print(f"Entry Date: {outlier['entry_date'].date()}")
        print(f"Entry Price: {outlier['entry_price']}")
        
        sym_df = df[(df['symbol'] == outlier['symbol']) & (df['date'] >= outlier['entry_date'])].copy()
        final_close = sym_df.loc[sym_df['date'] == max_date, 'close'].values[0]
        print(f"Final Close: {final_close}")
        print(f"Return: {(final_close/outlier['entry_price'] - 1)*100:.2f}%")
        
        # Let's print the OHLCV for this symbol around the huge move
        sym_df['prev_close'] = sym_df['close'].shift(1)
        sym_df['ret'] = sym_df['close'] / sym_df['prev_close'] - 1
        
        print("\nDiscontinuities (>20%):")
        huge = sym_df[abs(sym_df['ret']) > 0.2]
        for idx, row in huge.iterrows():
            print(f"{row['date'].date()} | Prev: {row['prev_close']:>8.2f} | Close: {row['close']:>8.2f} | Ret: {row['ret']*100:.2f}%")

if __name__ == '__main__':
    main()

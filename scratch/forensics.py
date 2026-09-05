import pandas as pd
import numpy as np

def main():
    df = pd.read_pickle('scratch/minervini_base.pkl')
    
    # 8. Secondary Outlier Scan (Top 20 Absolute Returns)
    print("\n--- OUTLIER SCAN (>50% moves) ---")
    df['prev_close'] = df.groupby('symbol')['close'].shift(1)
    df['daily_return'] = (df['close'] / df['prev_close']) - 1
    df['abs_return'] = abs(df['daily_return'])
    
    top_20 = df.sort_values('abs_return', ascending=False).head(20)
    for idx, row in top_20.iterrows():
        print(f"{row['symbol']} | {row['date'].date()} | Prev: {row['prev_close']} | Close: {row['close']} | Ret: {row['daily_return']*100:.2f}% | Vol: {row['volume']}")

if __name__ == '__main__':
    main()

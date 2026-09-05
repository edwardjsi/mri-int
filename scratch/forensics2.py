import pandas as pd

def main():
    df = pd.read_pickle('scratch/minervini_base.pkl')
    
    mrf = df[(df['symbol'] == 'MRF') & (df['date'] >= '2025-12-15') & (df['date'] <= '2026-02-15')].copy()
    mrf['prev_close'] = mrf['close'].shift(1)
    mrf['ret'] = mrf['close'] / mrf['prev_close'] - 1
    
    print("\n--- MRF FORENSICS ---")
    for idx, row in mrf.iterrows():
        if pd.isnull(row['prev_close']): continue
        print(f"{row['date'].date()} | Prev: {row['prev_close']:>10.2f} | Open: {row['open']:>10.2f} | High: {row['high']:>10.2f} | Low: {row['low']:>10.2f} | Close: {row['close']:>10.2f} | Vol: {row['volume']:>8.0f} | Ret: {row['ret']*100:>10.2f}%")

if __name__ == '__main__':
    main()

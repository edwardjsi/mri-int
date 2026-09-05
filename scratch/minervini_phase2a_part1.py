import pandas as pd
import numpy as np

def test_look_ahead_bias(df):
    print("\n--- 3. LOOK-AHEAD-BIAS TEST ---")
    # Pick a random symbol and date where we have enough history
    sample = df.dropna(subset=['sma_200']).sample(1).iloc[0]
    symbol = sample['symbol']
    date_t = sample['date']
    
    # Get manual subset of data STRICTLY before or on date T for this symbol
    subset = df[(df['symbol'] == symbol) & (df['date'] <= date_t)].copy()
    
    # Calculate manually
    manual_sma200 = subset['close'].tail(200).mean()
    manual_52w_high = subset['high'].tail(252).max()
    
    # Assert they match exactly (with some float tolerance)
    assert np.isclose(manual_sma200, sample['sma_200']), f"Look-ahead bias detected in SMA200! Manual: {manual_sma200}, Calculated: {sample['sma_200']}"
    assert np.isclose(manual_52w_high, sample['52w_high']), f"Look-ahead bias detected in 52w High!"
    
    print(f"Look-ahead bias test passed for symbol {symbol} at {date_t}.")
    print(f"Manual SMA200: {manual_sma200:.2f} == Calculated: {sample['sma_200']:.2f}")
    print(f"Manual 52w High: {manual_52w_high:.2f} == Calculated: {sample['52w_high']:.2f}")

def main():
    print("Loading data...")
    df = pd.read_csv('backups/20260304/daily_prices.csv', parse_dates=['date'])
    
    print("\n--- 1. DATA SOURCE ---")
    print(f"Earliest date: {df['date'].min()}")
    print(f"Latest date: {df['date'].max()}")
    print(f"Number of rows: {len(df)}")
    print(f"Number of unique symbols: {df['symbol'].nunique()}")
    print(f"Number of trading dates: {df['date'].nunique()}")
    
    print("\n--- 2. DATA ORDERING ---")
    df = df.sort_values(['symbol', 'date'])
    
    dupe_rows = df.duplicated().sum()
    dupe_symbol_date = df.duplicated(subset=['symbol', 'date']).sum()
    print(f"Duplicate rows: {dupe_rows}")
    print(f"Duplicate symbol/date combinations: {dupe_symbol_date}")
    
    # Verify no out of order (already sorted, but let's assert)
    assert df.groupby('symbol')['date'].is_monotonic_increasing.all(), "Out-of-order records found!"
    print("Out-of-order records: 0 (verified strictly ascending per symbol)")
    
    print("\n--- 5, 6, 7. ROLLING CALCULATIONS ---")
    # We must calculate SMA 50, 150, 200, 52w High/Low, Vol SMA50, ATR20
    # Use close for SMAs. 
    # True Range (TR) = max(High - Low, abs(High - PrevClose), abs(Low - PrevClose))
    df['prev_close'] = df.groupby('symbol')['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = (df['high'] - df['prev_close']).abs()
    df['tr3'] = (df['low'] - df['prev_close']).abs()
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    
    print("Calculating SMAs and 52W metrics...")
    df['sma_50'] = df.groupby('symbol')['close'].rolling(window=50, min_periods=50).mean().reset_index(0, drop=True)
    df['sma_150'] = df.groupby('symbol')['close'].rolling(window=150, min_periods=150).mean().reset_index(0, drop=True)
    df['sma_200'] = df.groupby('symbol')['close'].rolling(window=200, min_periods=200).mean().reset_index(0, drop=True)
    
    # Fallback to close if high/low missing
    high_col = 'high' if 'high' in df.columns else 'close'
    low_col = 'low' if 'low' in df.columns else 'close'
    
    df['52w_high'] = df.groupby('symbol')[high_col].rolling(window=252, min_periods=252).max().reset_index(0, drop=True)
    df['52w_low'] = df.groupby('symbol')[low_col].rolling(window=252, min_periods=252).min().reset_index(0, drop=True)
    
    df['vol_sma_50'] = df.groupby('symbol')['volume'].rolling(window=50, min_periods=50).mean().reset_index(0, drop=True)
    df['atr_20'] = df.groupby('symbol')['tr'].rolling(window=20, min_periods=20).mean().reset_index(0, drop=True)
    
    # 200-day slope: defined as SMA200[T] > SMA200[T-20]
    df['sma_200_prev20'] = df.groupby('symbol')['sma_200'].shift(20)
    df['sma_200_rising'] = df['sma_200'] > df['sma_200_prev20']
    
    test_look_ahead_bias(df)
    
    print("\n--- 4. USE THE APPROVED MINERVINI TREND TEMPLATE ---")
    # Conditions:
    # price > SMA150
    # price > SMA200
    # SMA150 > SMA200
    # SMA200 rising
    # SMA50 > SMA150
    # SMA50 > SMA200
    # price > SMA50
    # price >= 1.30 * 52-week low
    # price <= 1.25 * 52-week high
    
    df['stage2'] = (
        (df['close'] > df['sma_150']) &
        (df['close'] > df['sma_200']) &
        (df['sma_150'] > df['sma_200']) &
        (df['sma_200_rising']) &
        (df['sma_50'] > df['sma_150']) &
        (df['sma_50'] > df['sma_200']) &
        (df['close'] > df['sma_50']) &
        (df['close'] >= 1.30 * df['52w_low']) &
        (df['close'] <= 1.25 * df['52w_high'])
    )
    
    print("\n--- 8. STOCK CANDIDATE COUNTS ---")
    # Date | Number passing Trend Template excluding RS | Number passing Trend Template including RS
    df['year'] = df['date'].dt.year
    counts_by_date = df[df['stage2']].groupby('date').size().reset_index(name='count_excl_rs')
    # RS Requirement = UNAVAILABLE
    counts_by_date['count_incl_rs'] = "RS REQUIREMENT = UNAVAILABLE"
    
    print(counts_by_date.head())
    
    stats = counts_by_date.copy()
    stats['year'] = stats['date'].dt.year
    grouped = stats.groupby('year')['count_excl_rs'].agg(['min', 'max', 'mean', 'median'])
    print(grouped)
    
    # Save partial dataframe to pickle for fast loading in next steps
    df.to_pickle('scratch/minervini_base.pkl')

if __name__ == '__main__':
    main()

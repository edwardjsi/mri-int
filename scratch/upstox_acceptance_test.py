import os
import sys
import time
import json
import io
import requests
import pandas as pd
from datetime import datetime, timedelta

def main():
    print("==================================================")
    print("UPSTOX PHASE 1 — DATA ACCEPTANCE TEST")
    print("==================================================")

    token = os.environ.get("UPSTOX_ACCESS_TOKEN")
    if not token:
        print("ERROR: UPSTOX_ACCESS_TOKEN environment variable not set.")
        print("Please set the token and re-run this script.")
        sys.exit(1)
        
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    # 1. Download Instrument Metadata
    print("\nDownloading Upstox Instrument Metadata...")
    try:
        url = 'https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz'
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        instruments_df = pd.read_csv(io.BytesIO(r.content), compression='gzip')
        print(f"Loaded {len(instruments_df)} instruments from NSE.")
    except Exception as e:
        print(f"Failed to fetch instrument metadata: {e}")
        try:
            url = 'https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz'
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            instruments_df = pd.read_csv(io.BytesIO(r.content), compression='gzip')
            print(f"Loaded {len(instruments_df)} instruments from Complete list.")
        except Exception as e2:
            print("Failed completely.")
            sys.exit(1)

    # 2. Locate Test Instruments
    test_symbols = ['MRF', 'BAJFINANCE', 'HINDZINC', 'BEL', 'CIPLA', 'RELIANCE', 'TCS', 'INFY']
    test_symbols += ['JIOFIN', 'LTIM'] 
    
    test_instruments = []
    
    for sym in test_symbols:
        matches = instruments_df[instruments_df['tradingsymbol'] == sym + "-EQ"]
        if matches.empty:
            matches = instruments_df[instruments_df['tradingsymbol'] == sym]
        if not matches.empty:
            test_instruments.append(matches.iloc[0])
        else:
            print(f"Could not find instrument for {sym}")

    print(f"\nFound {len(test_instruments)} test instruments:")
    for inst in test_instruments:
        print(f"{inst['tradingsymbol']} - {inst['instrument_key']} - {inst['isin']}")

    # 3. Retrieve Daily Candles (V3)
    def fetch_historical_v3(instrument_key, from_date, to_date):
        endpoint = f"https://api.upstox.com/v3/historical-candle/{instrument_key}/days/1/{to_date}/{from_date}"
        resp = requests.get(endpoint, headers=headers)
        if resp.status_code == 429:
            print("Rate limit hit, sleeping...")
            time.sleep(5)
            return fetch_historical_v3(instrument_key, from_date, to_date)
        if resp.status_code != 200:
            print(f"API Error {resp.status_code}: {resp.text}")
            return []
        
        return resp.json().get('data', {}).get('candles', [])

    def get_full_history(instrument_key):
        start_date = datetime(2000, 1, 1)
        end_date = datetime.now()
        all_candles = []
        
        curr_start = start_date
        while curr_start < end_date:
            curr_end = min(curr_start + timedelta(days=365*9), end_date)
            print(f"Fetching {instrument_key} from {curr_start.strftime('%Y-%m-%d')} to {curr_end.strftime('%Y-%m-%d')}")
            
            candles = fetch_historical_v3(instrument_key, curr_start.strftime('%Y-%m-%d'), curr_end.strftime('%Y-%m-%d'))
            if candles:
                all_candles.extend(candles)
            
            curr_start = curr_end + timedelta(days=1)
            time.sleep(1)
            
        return all_candles

    mrf_key = next((i['instrument_key'] for i in test_instruments if 'MRF' in i['tradingsymbol']), None)
    if mrf_key:
        print("\nTesting MRF History...")
        mrf_data = get_full_history(mrf_key)
        print(f"Retrieved {len(mrf_data)} candles for MRF")
        if mrf_data:
            df = pd.DataFrame(mrf_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp').sort_index()
            
            print("\n--- MRF BAD-TICK TEST ---")
            for d in ['2026-01-14', '2026-01-15', '2026-01-16', '2026-01-19']:
                try:
                    # Using string slicing for dates just in case time is attached
                    mask = df.index.astype(str).str.startswith(d)
                    if mask.any():
                        row = df[mask].iloc[0]
                        print(f"{d} - Close: {row['close']} | High: {row['high']} | Low: {row['low']}")
                    else:
                        print(f"{d} - NO DATA")
                except Exception as e:
                    print(f"{d} - ERROR: {e}")
                    
    print("\nAcceptance Test Script Execution Complete.")

if __name__ == "__main__":
    main()

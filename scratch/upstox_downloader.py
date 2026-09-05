import os
import sys
import time
import json
import io
import requests
import pandas as pd
from datetime import datetime, timedelta

def main():
    token = os.environ.get("UPSTOX_ACCESS_TOKEN")
    if not token:
        print("ERROR: UPSTOX_ACCESS_TOKEN environment variable not set.")
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
    except Exception as e:
        url = 'https://assets.upstox.com/market-quote/instruments/exchange/complete.csv.gz'
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        instruments_df = pd.read_csv(io.BytesIO(r.content), compression='gzip')

    test_symbols = ['MRF', 'BAJFINANCE', 'HINDZINC', 'BEL', 'CIPLA', 'RELIANCE', 'TCS', 'INFY', 'JIOFIN', 'LTIM']
    
    test_instruments = []
    for sym in test_symbols:
        matches = instruments_df[instruments_df['tradingsymbol'] == sym + "-EQ"]
        if matches.empty:
            matches = instruments_df[instruments_df['tradingsymbol'] == sym]
        if not matches.empty:
            test_instruments.append(matches.iloc[0])

    # NIFTY 500
    nifty500 = instruments_df[instruments_df['tradingsymbol'] == 'NIFTY 500']
    if not nifty500.empty:
        test_instruments.append(nifty500.iloc[0])

    def fetch_historical_v3(instrument_key, from_date, to_date):
        endpoint = f"https://api.upstox.com/v3/historical-candle/{instrument_key}/days/1/{to_date}/{from_date}"
        resp = requests.get(endpoint, headers=headers)
        if resp.status_code == 429:
            print("Rate limit hit, sleeping 5s...")
            time.sleep(5)
            return fetch_historical_v3(instrument_key, from_date, to_date)
        if resp.status_code != 200:
            print(f"API Error {resp.status_code}: {resp.text}")
            return []
        return resp.json().get('data', {}).get('candles', [])

    def fetch_corporate_actions(isin):
        endpoint = f"https://api.upstox.com/v2/fundamentals/{isin}/corporate-actions"
        resp = requests.get(endpoint, headers=headers)
        if resp.status_code == 200:
            return resp.json().get('data', [])
        return []

    for inst in test_instruments:
        symbol = inst['tradingsymbol']
        inst_key = inst['instrument_key']
        isin = inst.get('isin', '')
        
        print(f"\nProcessing {symbol} ({inst_key})")
        
        # Check if already downloaded
        file_path = f"scratch/{symbol}_candles.json"
        if not os.path.exists(file_path):
            start_date = datetime(2000, 1, 1)
            end_date = datetime.now()
            all_candles = []
            
            curr_start = start_date
            while curr_start < end_date:
                curr_end = min(curr_start + timedelta(days=365*9), end_date)
                print(f"  Fetching from {curr_start.strftime('%Y-%m-%d')} to {curr_end.strftime('%Y-%m-%d')}")
                
                candles = fetch_historical_v3(inst_key, curr_start.strftime('%Y-%m-%d'), curr_end.strftime('%Y-%m-%d'))
                if candles:
                    all_candles.extend(candles)
                
                curr_start = curr_end + timedelta(days=1)
                time.sleep(0.5)
                
            with open(file_path, "w") as f:
                json.dump(all_candles, f)
        
        ca_path = f"scratch/{symbol}_ca.json"
        if isin and not os.path.exists(ca_path):
            cas = fetch_corporate_actions(isin)
            with open(ca_path, "w") as f:
                json.dump(cas, f)
                
    print("\nData download complete.")

if __name__ == "__main__":
    main()

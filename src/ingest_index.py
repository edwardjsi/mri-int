import os
import sys
import datetime
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

# Ensure we're reading the local DB
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from src.db import insert_index_prices

START_DATE = "2003-01-01"
END_DATE = datetime.datetime.today().strftime("%Y-%m-%d")

def run():
    print("Fetching NIFTY 50 index data for Relative Strength (RS) calculations...")
    raw = yf.download("^NSEI", start=START_DATE, end=END_DATE, progress=False, auto_adjust=True)
    if raw.empty:
        print("Failed to download ^NSEI from yfinance.")
        return
        
    df = raw.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower().replace(" ", "_") for col in df.columns]
    else:
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]

    if "close" not in df.columns and "adj_close" in df.columns:
        df["close"] = df["adj_close"]

    for col in ["open", "high", "low"]:
        if col not in df.columns:
            df[col] = df["close"]
    if "volume" not in df.columns:
        df["volume"] = 0

    df["symbol"] = "NIFTY50"
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df[["symbol", "date", "open", "high", "low", "close", "volume"]]
    df = df.dropna(subset=["close"])
    
    records = df.to_dict("records")
    insert_index_prices(records)
    print(f"Successfully inserted {len(records)} index rows for NIFTY50.")

if __name__ == "__main__":
    run()

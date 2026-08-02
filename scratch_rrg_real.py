import pandas as pd
from engine_core.db import get_connection
from engine_core.rrg_indicators import compute_rrg_indicators

def test_real_data(symbol):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT date, close FROM daily_prices WHERE symbol = %s ORDER BY date", (symbol,))
            stock_rows = cur.fetchall()
            
            cur.execute("SELECT date, close as idx_close FROM market_index_prices WHERE symbol = 'NIFTY50' ORDER BY date")
            idx_rows = cur.fetchall()
            
            s_df = pd.DataFrame([dict(r) for r in stock_rows])
            i_df = pd.DataFrame([dict(r) for r in idx_rows])
            
            if s_df.empty or i_df.empty:
                print(f"No data for {symbol}")
                return
                
            s_df["date"] = pd.to_datetime(s_df["date"])
            s_df["close"] = pd.to_numeric(s_df["close"])
            i_df["date"] = pd.to_datetime(i_df["date"])
            i_df["idx_close"] = pd.to_numeric(i_df["idx_close"])
            
            merged = pd.merge(s_df, i_df, on="date", how="inner").set_index("date")
            
            rrg_df = compute_rrg_indicators(merged["close"], merged["idx_close"], window=14)
            print(f"--- RRG Output for {symbol} ---")
            print(rrg_df.tail())
            
    finally:
        conn.close()

if __name__ == "__main__":
    for sym in ["GRANULES", "POLYCAB", "TCS"]:
        test_real_data(sym)

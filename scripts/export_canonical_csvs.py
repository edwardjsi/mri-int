import os
import pandas as pd
from engine_core.db import get_connection

def export_canonical_csvs():
    os.makedirs("backups/20260304", exist_ok=True)
    conn = get_connection()
    
    print("📤 Exporting daily_prices.csv...")
    # Fetch data needed for backtest (ema_50, ema_200, rs_90d, rolling_high_6m)
    # The backtest script expects specific columns.
    query = """
        SELECT symbol, date, open, high, low, close, volume, 
               ema_50, ema_200, rs_90d, rolling_high_6m, avg_volume_20d, ema_200_slope_20
        FROM daily_prices
        ORDER BY symbol, date
    """
    df = pd.read_sql(query, conn)
    df.to_csv("backups/20260304/daily_prices.csv", index=False)
    print(f"✅ Saved backups/20260304/daily_prices.csv ({len(df)} rows)")
    
    print("📤 Exporting index_prices.csv...")
    query = """
        SELECT symbol, date, open, high, low, close, volume
        FROM market_index_prices
        ORDER BY symbol, date
    """
    df_idx = pd.read_sql(query, conn)
    df_idx.to_csv("backups/20260304/index_prices.csv", index=False)
    print(f"✅ Saved backups/20260304/index_prices.csv ({len(df_idx)} rows)")
    
    conn.close()

if __name__ == "__main__":
    export_canonical_csvs()

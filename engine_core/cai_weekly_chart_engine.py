import logging
import pandas as pd
from datetime import datetime, timedelta
from engine_core.db import get_connection

logger = logging.getLogger(__name__)

def generate_weekly_candles(symbol: str, years: int = 3):
    """
    Fetch daily prices for a given symbol and aggregate them into weekly candlesticks.
    Calculates 10-week and 40-week EMAs.
    Returns a list of dictionaries formatted for frontend charting libraries (like lightweight-charts).
    """
    conn = get_connection()
    try:
        start_date = datetime.now() - timedelta(days=years * 365)
        
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT date, open, high, low, close, volume
                FROM daily_prices
                WHERE symbol = %s AND date >= %s
                ORDER BY date ASC
                """,
                (symbol, start_date.date())
            )
            rows = cur.fetchall()
            
        if not rows:
            return []

        df = pd.DataFrame([dict(r) for r in rows])
        df["date"] = pd.to_datetime(df["date"])
        
        # Ensure numeric types
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
        # Set date as index for resampling
        df.set_index("date", inplace=True)
        
        # Aggregate to weekly (ending on Friday)
        weekly_df = df.resample("W-FRI").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna()
        
        # Calculate Weekly EMAs
        weekly_df["ema_10"] = weekly_df["close"].ewm(span=10, adjust=False).mean()
        weekly_df["ema_40"] = weekly_df["close"].ewm(span=40, adjust=False).mean()
        
        # Round values for clean frontend consumption
        weekly_df = weekly_df.round({
            "open": 2, "high": 2, "low": 2, "close": 2, "ema_10": 2, "ema_40": 2
        })
        
        # Format for lightweight-charts: time (YYYY-MM-DD), open, high, low, close, etc.
        results = []
        for index, row in weekly_df.iterrows():
            results.append({
                "time": index.strftime("%Y-%m-%d"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
                "ema10": float(row["ema_10"]) if pd.notna(row["ema_10"]) else None,
                "ema40": float(row["ema_40"]) if pd.notna(row["ema_40"]) else None
            })
            
        return results

    except Exception as e:
        logger.error(f"Failed to generate weekly candles for {symbol}: {e}")
        return []
    finally:
        conn.close()

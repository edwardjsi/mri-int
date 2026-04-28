import pandas as pd
from typing import List, Dict
from engine_core.db import get_connection

def run_quality_backtest(symbol: str):
    """Simulate returns for a stock based on score improvement entries."""
    conn = get_connection()
    
    # 1. Fetch Price History
    prices_df = pd.read_sql(f"SELECT date, close FROM daily_prices WHERE symbol = '{symbol}' ORDER BY date ASC", conn)
    
    # 2. Fetch Score History
    scores_df = pd.read_sql(f"SELECT recorded_at::date as date, score FROM quality_verdicts_history WHERE symbol = '{symbol}' ORDER BY recorded_at ASC", conn)
    
    conn.close()
    
    if prices_df.empty or scores_df.empty:
        return {"error": "Insufficient data"}
        
    # Merge on date
    df = pd.merge(prices_df, scores_df, on="date", how="left").ffill()
    
    trades = []
    in_position = False
    entry_price = 0
    entry_date = None
    
    for i in range(1, len(df)):
        score = df.iloc[i]['score']
        prev_score = df.iloc[i-1]['score']
        price = df.iloc[i]['close']
        date = df.iloc[i]['date']
        
        # ENTRY: Score > 70 and Score is improving
        if not in_position and score > 70 and score > prev_score:
            in_position = True
            entry_price = price
            entry_date = date
            
        # EXIT: Score drops below 60 or after 20 trading days (simple proxy)
        elif in_position and (score < 60 or (pd.to_datetime(date) - pd.to_datetime(entry_date)).days > 30):
            exit_price = price
            return_pct = (exit_price - entry_price) / entry_price
            trades.append({
                "entry_date": entry_date,
                "exit_date": date,
                "return": return_pct
            })
            in_position = False

    if not trades:
        return {"symbol": symbol, "total_return": 0, "trades": 0}
        
    avg_return = sum(t['return'] for t in trades) / len(trades)
    win_rate = len([t for t in trades if t['return'] > 0]) / len(trades)
    
    return {
        "symbol": symbol,
        "trades": len(trades),
        "avg_return": round(avg_return * 100, 2),
        "win_rate": round(win_rate * 100, 2),
        "total_trades": trades
    }

if __name__ == "__main__":
    print(run_quality_backtest("RELIANCE.NS"))

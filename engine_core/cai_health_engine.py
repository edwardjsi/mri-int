import logging
from engine_core.cai_weekly_chart_engine import generate_weekly_candles
from engine_core.db import get_connection

logger = logging.getLogger(__name__)

def compute_position_health(symbol: str) -> float:
    """
    Computes a 0-100 health score for a currently held position based on:
    - Weekly Price vs EMA10 (30 pts)
    - Weekly Price vs EMA40 (30 pts)
    - Relative Strength (rs_90d) Maintenance (20 pts)
    - Distribution / Volume (20 pts)
    """
    try:
        # 1. Fetch Weekly Data
        weekly_data = generate_weekly_candles(symbol, years=1)
        if not weekly_data or len(weekly_data) < 2:
            return 50.0  # Default neutral score if not enough data
            
        latest_week = weekly_data[-1]
        close = latest_week["close"]
        ema10 = latest_week["ema10"]
        ema40 = latest_week["ema40"]
        
        score = 0.0
        
        # 1. Price vs EMA10 (30 pts)
        if ema10 and close > ema10:
            score += 30
        elif ema10 and close > (ema10 * 0.97):
            score += 15 # Within 3% of EMA10
            
        # 2. Price vs EMA40 (30 pts)
        if ema40 and close > ema40:
            score += 30
        elif ema40 and close > (ema40 * 0.95):
            score += 10 # Within 5% of EMA40
            
        # 3. Fetch latest RS and Volume from daily_prices
        conn = get_connection()
        rs_score = 0
        distribution_score = 20 # Start full, deduct for bad volume
        
        try:
            with conn.cursor() as cur:
                # RS check
                cur.execute(
                    "SELECT rs_90d, volume, avg_volume_20d, close, open FROM daily_prices WHERE symbol = %s ORDER BY date DESC LIMIT 10", 
                    (symbol,)
                )
                recent_days = cur.fetchall()
                if recent_days:
                    latest_rs = recent_days[0]['rs_90d']
                    if latest_rs and latest_rs > 0:
                        rs_score = 20
                    elif latest_rs and latest_rs > -2.0:
                        rs_score = 10
                        
                    # Distribution check: count down days with volume > avg
                    dist_days = 0
                    for day in recent_days:
                        vol = day['volume']
                        avg_vol = day['avg_volume_20d']
                        day_close = day['close']
                        day_open = day['open']
                        if day_close and day_open and day_close < day_open and vol and avg_vol and vol > avg_vol:
                            dist_days += 1
                            
                    if dist_days >= 3:
                        distribution_score = 0
                    elif dist_days == 2:
                        distribution_score = 10
        finally:
            conn.close()
            
        score += rs_score
        score += distribution_score
        
        return round(max(0.0, min(100.0, score)), 2)
        
    except Exception as e:
        logger.error(f"Failed to compute health for {symbol}: {e}")
        return 50.0

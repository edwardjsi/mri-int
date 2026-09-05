from engine_core.cai_weekly_chart_engine import generate_weekly_candles
import json

candles = generate_weekly_candles("SHAILY", 3)
print(f"Total candles: {len(candles)}")
if candles:
    print(json.dumps(candles[0], indent=2))
    print(json.dumps(candles[-1], indent=2))

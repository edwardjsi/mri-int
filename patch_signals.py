import re

with open('api/signals.py', 'r') as f:
    content = f.read()

# 1. Shadow signals:
content = content.replace('dp.close\n            FROM public.stock_scores s', 'dp.close, dp.breakout_state\n            FROM public.stock_scores s')
content = content.replace("c_breakout, c_quality, close = r['condition_breakout_10d'], r['condition_price_quality'], r['close']", "c_breakout, c_quality, close = r['condition_breakout_10d'], r['condition_price_quality'], r['close']\n                breakout_state = r.get('breakout_state', 'CONSOLIDATING')")
content = content.replace("sym, score, dt, c_ema, c_slope, c_high, c_vol, c_rs, c_breakout, c_quality, close = r", "sym, score, dt, c_ema, c_slope, c_high, c_vol, c_rs, c_breakout, c_quality, close, breakout_state = r")
content = content.replace('"is_breakout": is_breakout', '"is_breakout": is_breakout,\n                "breakout_state": breakout_state')

# 2. Today's signals:
content = content.replace('ss.condition_breakout_10d, ss.condition_price_quality\n        FROM client_signals cs\n        LEFT JOIN client_actions ca ON ca.signal_id = cs.id\n        LEFT JOIN LATERAL (', 'ss.condition_breakout_10d, ss.condition_price_quality, dp.breakout_state\n        FROM client_signals cs\n        LEFT JOIN client_actions ca ON ca.signal_id = cs.id\n        LEFT JOIN LATERAL (')
content = content.replace(') ss ON true\n        WHERE cs.client_id = %s\n          AND cs.date', ') ss ON true\n        LEFT JOIN daily_prices dp ON dp.symbol = cs.symbol AND dp.date = cs.date\n        WHERE cs.client_id = %s\n          AND cs.date')
content = content.replace('"quantity": s["quantity"] if is_dict else s[10],', '"quantity": s["quantity"] if is_dict else s[10],\n                "breakout_state": s.get("breakout_state", "CONSOLIDATING") if is_dict else (s[18] if len(s) > 18 else "CONSOLIDATING"),')

# 3. Pending signals:
content = content.replace(') ss ON true\n        WHERE cs.client_id = %s\n          AND ca.id IS NULL', ') ss ON true\n        LEFT JOIN daily_prices dp ON dp.symbol = cs.symbol AND dp.date = cs.date\n        WHERE cs.client_id = %s\n          AND ca.id IS NULL')

# 4. History signals:
content = content.replace(') ss ON true\n        WHERE cs.client_id = %s\n          AND cs.date >=', ') ss ON true\n        LEFT JOIN daily_prices dp ON dp.symbol = cs.symbol AND dp.date = cs.date\n        WHERE cs.client_id = %s\n          AND cs.date >=')

with open('api/signals.py', 'w') as f:
    f.write(content)
print("api/signals.py patched")

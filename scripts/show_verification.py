"""Show verification results for a symbol."""
import sys
from engine_core.db import get_connection

symbol = sys.argv[1] if len(sys.argv) > 1 else "TCS"
conn = get_connection()
cur = conn.cursor()
cur.execute(
    """SELECT g.guidance_type, g.guidance_text, g.target_value,
              v.status, v.actual_value, v.variance_pct
       FROM management_guidance g
       LEFT JOIN guidance_verification v ON g.id = v.guidance_id
       WHERE g.symbol = %s ORDER BY g.id""",
    (symbol,),
)
rows = cur.fetchall()
print(f"\n=== {symbol}: Verification Results ===\n")
for i, r in enumerate(rows, 1):
    get = lambda j: r[j] if isinstance(r, (list, tuple)) else list(r.values())[j]
    gtype, text, target, status, actual, varp = get(0), get(1), get(2), get(3), get(4), get(5)
    icon = {"ACHIEVED": "✅", "MISSED": "❌", "PARTIAL": "⚠️", "PENDING": "⏳"}.get(status, "⚡")
    print(f"{icon} [{gtype:20s}] {text[:80]}")
    if target:
        print(f"   Target: {target} | Actual: {actual} | Variance: {varp} | {status}")
    else:
        print(f"   Status: {status}")
    print()
conn.close()

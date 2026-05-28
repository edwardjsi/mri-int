"""Show extracted guidance for a symbol."""
import sys
from engine_core.db import get_connection

symbol = sys.argv[1] if len(sys.argv) > 1 else "TCS"
conn = get_connection()
cur = conn.cursor()
cur.execute(
    """SELECT id, guidance_type, guidance_text, target_value,
              target_unit, target_date, confidence
       FROM public.management_guidance
       WHERE symbol = %s ORDER BY id""",
    (symbol,),
)
rows = cur.fetchall()
print(f"\n=== {symbol}: {len(rows)} guidance statements ===\n")
for r in rows:
    gtype = r[1] if isinstance(r, (list, tuple)) else r["guidance_type"]
    gtext = r[2] if isinstance(r, (list, tuple)) else r["guidance_text"]
    tval = r[3] if isinstance(r, (list, tuple)) else r["target_value"]
    tunit = r[4] if isinstance(r, (list, tuple)) else r["target_unit"]
    tdate = r[5] if isinstance(r, (list, tuple)) else r["target_date"]
    conf = r[6] if isinstance(r, (list, tuple)) else r["confidence"]
    print(f"[{gtype}] {gtext}")
    if tval:
        print(f"  → Target: {tval} {tunit} by {tdate} | Confidence: {conf}")
    print()
conn.close()

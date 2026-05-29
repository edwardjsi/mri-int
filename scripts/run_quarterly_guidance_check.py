#!/usr/bin/env python3
"""
Quarterly Guidance Check — verifies management promises against latest financials.
Run after quarterly results are ingested. Shows promises kept vs broken.

Usage:
    python3 scripts/run_quarterly_guidance_check.py
    python3 scripts/run_quarterly_guidance_check.py --due
"""

import sys
from datetime import date
from engine_core.db import get_connection, fetch_df
from engine_guidance.guidance_verifier import GuidanceVerifier, parse_target_quarter, calendar_to_fiscal
from engine_guidance.credibility_scorer import CredibilityScorer

def run():
    df = fetch_df("SELECT DISTINCT symbol FROM management_guidance ORDER BY symbol")
    symbols = df["symbol"].tolist() if not df.empty else []
    if not symbols:
        print("No tracked companies.")
        return

    today = date.today()
    cfy, cfq = calendar_to_fiscal(today)

    # Show promises due
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""SELECT g.id, g.symbol, g.guidance_type, g.guidance_text, g.target_value, g.target_unit, g.target_date
                   FROM management_guidance g LEFT JOIN guidance_verification v ON g.id=v.guidance_id
                   WHERE v.id IS NULL OR v.status='PENDING' ORDER BY g.symbol""")
    due = []
    for r in cur.fetchall():
        gid, sym, gtype, gtext, tval, tunit, tdate = (r[0],r[1],r[2],r[3],r[4],r[5],r[6]) if isinstance(r,tuple) else (r["id"],r["symbol"],r["guidance_type"],r["guidance_text"],r["target_value"],r["target_unit"],r["target_date"])
        parsed = parse_target_quarter(tdate or "")
        if parsed:
            fy, fq = parsed
            if fy < cfy or (fy == cfy and fq <= cfq):
                due.append((sym, gtype, gtext, tval, tunit, fq, fy))
    conn.close()

    if due:
        print(f"PROMISES DUE ({len(due)}):")
        for d in due:
            print(f"  {d[0]:12s} [{d[1]:20s}] {d[2][:60]}")
            if d[3]:
                print(f"    Target: {d[3]} {d[4]} by Q{d[5]}FY{str(d[6])[-2:]}")
        print()

    # Verify all
    verifier = GuidanceVerifier()
    scorer = CredibilityScorer()
    total = 0
    for sym in symbols:
        r = verifier.verify_symbol(sym)
        total += r.get("verified", 0)
    print(f"Verified: {total} new. Updating scores...")

    for sym in symbols:
        result = scorer.compute_score(sym)
        if result["total_promises"] > 0:
            print(f"  {sym:12s} {result['accuracy_pct']:5.1f}% ({result['achieved']}/{result['total_promises']}) {result['trend']}")

if __name__ == "__main__":
    run()

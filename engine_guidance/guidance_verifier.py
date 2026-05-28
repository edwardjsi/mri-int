"""
Guidance Verifier — checks management promises against actual quarterly results.

Usage:
    python3 -m engine_guidance.guidance_verifier --symbol TCS
"""

import logging
from datetime import date

from engine_core.db import get_connection

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("guidance_verifier")

# ── Guidance Type → Financial Column Mapping ─────────────────────────────
MAPPING = {
    "MARGIN": {
        "sql": """SELECT CASE WHEN revenue > 0
                  THEN (ebitda::NUMERIC / revenue::NUMERIC) * 100
                  ELSE NULL END AS actual
                  FROM aae_quarterly_financials
                  WHERE symbol=%s AND year=%s AND quarter=%s""",
        "label": "EBITDA margin (%)",
    },
    "REVENUE_GROWTH": {
        "sql": """SELECT CASE WHEN prev.revenue > 0
                  THEN ((cur.revenue - prev.revenue) / prev.revenue) * 100.0
                  ELSE NULL END AS actual
                  FROM (SELECT revenue FROM aae_quarterly_financials
                        WHERE symbol=%s AND year=%s AND quarter=%s) cur,
                       (SELECT revenue FROM aae_quarterly_financials
                        WHERE symbol=%s
                          AND (year=%s - CASE WHEN %s=1 THEN 1 ELSE 0 END)
                          AND quarter=CASE WHEN %s=1 THEN 4 ELSE %s-1 END) prev""",
        "label": "Revenue QoQ growth (%)",
    },
    "CAPEX": {
        "sql": """SELECT capex AS actual
                  FROM aae_quarterly_financials
                  WHERE symbol=%s AND year=%s AND quarter=%s""",
        "label": "Capex",
    },
    "DEBT_REDUCTION": {
        "sql": """SELECT debt AS actual
                  FROM aae_quarterly_financials
                  WHERE symbol=%s AND year=%s AND quarter=%s""",
        "label": "Total debt",
    },
    "WORKING_CAPITAL": {
        "sql": """SELECT (COALESCE(receivables,0)+COALESCE(inventory,0)
                  -COALESCE(current_liabilities,0)) AS actual
                  FROM aae_quarterly_financials
                  WHERE symbol=%s AND year=%s AND quarter=%s""",
        "label": "Working capital",
    },
}


def parse_target_quarter(target_str: str) -> tuple | None:
    """Parse 'Q4FY26' → (2026, 4), 'FY26' → (2026, 4)."""
    if not target_str:
        return None
    s = target_str.upper().replace(" ", "")
    try:
        if "Q" in s and "FY" in s:
            q = int(s.split("FY")[0].replace("Q", ""))
            fy = 2000 + int(s.split("FY")[1])
            return (fy, q)
        if s.startswith("FY"):
            return (2000 + int(s[2:]), 4)
    except (ValueError, IndexError):
        pass
    return None


def calendar_to_fiscal(d: date) -> tuple:
    """Map calendar date to Indian fiscal quarter."""
    m = d.month
    if 4 <= m <= 6:    return (d.year, 1)
    elif 7 <= m <= 9:  return (d.year, 2)
    elif 10 <= m <= 12: return (d.year, 3)
    else:               return (d.year, 4)


class GuidanceVerifier:
    """Checks management guidance against actual quarterly financials."""

    def verify_guidance(self, guidance_id: int) -> str | None:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT id, symbol, guidance_type, target_value,
                          target_date FROM public.management_guidance
                   WHERE id=%s""",
                (guidance_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            get = lambda i: row[i] if isinstance(row, (list, tuple)) else list(row.values())[i]
            sid, sym, gtype, target, tdate_str = get(0), get(1), get(2), get(3), get(4)

            if not gtype or gtype not in MAPPING or not target:
                return self._store(cur, sid, None, None, "UNABLE_TO_VERIFY")

            parsed = parse_target_quarter(tdate_str or "")
            if not parsed:
                parsed = self._latest_fiscal_quarter(cur, sym)

            fy, fq = parsed
            cfy, cfq = calendar_to_fiscal(date.today())
            if fy > cfy or (fy == cfy and fq > cfq):
                return self._store(cur, sid, fy, fq, "PENDING")

            sql = MAPPING[gtype]["sql"]
            if gtype == "REVENUE_GROWTH":
                cur.execute(sql, (sym, fy, fq, sym, fy, fq, fq, fq))
            else:
                cur.execute(sql, (sym, fy, fq))

            r = cur.fetchone()
            if not r:
                return self._store(cur, sid, fy, fq, "UNABLE_TO_VERIFY")

            actual = r[0] if isinstance(r, (list, tuple)) else list(r.values())[0]
            if actual is None:
                return self._store(cur, sid, fy, fq, "UNABLE_TO_VERIFY")

            variance = ((float(actual) - float(target)) / abs(float(target))) * 100
            if abs(variance) <= 10:
                status = "ACHIEVED"
            elif abs(variance) <= 20:
                status = "PARTIAL"
            else:
                status = "MISSED"

            return self._store(cur, sid, fy, fq, status, actual, variance)
        finally:
            conn.close()

    def _latest_fiscal_quarter(self, cur, symbol):
        """Get the most recent fiscal quarter with data."""
        cur.execute(
            """SELECT year, quarter FROM aae_quarterly_financials
               WHERE symbol=%s ORDER BY year DESC, quarter DESC LIMIT 1""",
            (symbol,),
        )
        r = cur.fetchone()
        if r:
            return (r[0], r[1]) if isinstance(r, (list, tuple)) else (r["year"], r["quarter"])
        return calendar_to_fiscal(date.today())

    def _store(self, cur, gid, fy, fq, status, actual=None, variance=None):
        try:
            cur.execute(
                """INSERT INTO public.guidance_verification
                   (guidance_id, checked_fiscal_year, checked_fiscal_quarter,
                    actual_value, status, variance_pct)
                   VALUES (%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (guidance_id, checked_fiscal_year, checked_fiscal_quarter)
                   DO UPDATE SET actual_value=EXCLUDED.actual_value,
                                 status=EXCLUDED.status,
                                 variance_pct=EXCLUDED.variance_pct,
                                 verified_at=NOW()""",
                (gid, fy, fq, actual, status, variance),
            )
            cur.connection.commit()
        except Exception as e:
            logger.error(f"Store error: {e}")
        return status

    def verify_symbol(self, symbol: str) -> dict:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT g.id FROM public.management_guidance g
                   LEFT JOIN public.guidance_verification v ON g.id=v.guidance_id
                   WHERE g.symbol=%s AND v.id IS NULL""",
                (symbol.upper(),),
            )
            pending = [r[0] if isinstance(r, (list, tuple)) else list(r.values())[0]
                       for r in cur.fetchall()]
        finally:
            conn.close()

        results = {"verified": 0, "pending": 0, "unable": 0}
        for gid in pending:
            s = self.verify_guidance(gid)
            if s == "PENDING":         results["pending"] += 1
            elif s == "UNABLE_TO_VERIFY": results["unable"] += 1
            elif s:                     results["verified"] += 1
        logger.info(f"{symbol}: {results}")
        return results


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", "-s", required=True)
    args = ap.parse_args()
    v = GuidanceVerifier()
    r = v.verify_symbol(args.symbol)
    print(f"\n{args.symbol}: {r}")

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
        # YoY growth: compare same quarter of prior year
        "sql": """WITH cur AS (
                      SELECT revenue FROM aae_quarterly_financials
                      WHERE symbol=%s AND year=%s AND quarter=%s
                  ),
                  prev AS (
                      SELECT revenue FROM aae_quarterly_financials
                      WHERE symbol=%s AND year=%s-1 AND quarter=%s
                  )
                  SELECT CASE WHEN prev.revenue > 0
                      THEN ((cur.revenue - prev.revenue)::NUMERIC / prev.revenue) * 100.0
                      ELSE NULL END AS actual
                  FROM cur, prev""",
        "label": "Revenue YoY growth (%)",
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
    # Capacity / network expansion (transmission km, store count, plant MW, etc.)
    # No quarterly financial column tracks this — record value but mark UNABLE
    # with a reason so the UI can explain the gap to the user.
    "CAPACITY_EXPANSION": {
        "sql": """SELECT NULL::NUMERIC AS actual""",
        "label": "Capacity addition (units not in DB)",
        "reason": "no financial column for capacity — needs BSE filings / annual report data",
    },
    # Deal pipeline / order book (qualitative directional)
    "DEAL_PIPELINE": {
        "sql": """SELECT NULL::NUMERIC AS actual""",
        "label": "Order book / deal pipeline",
        "reason": "qualitative metric — not tracked in quarterly financials",
    },
    # Market share (qualitative)
    "MARKET_SHARE": {
        "sql": """SELECT NULL::NUMERIC AS actual""",
        "label": "Market share",
        "reason": "qualitative metric — needs industry data not in DB",
    },
    # Catch-all for types without a numeric financial mapping. Always UNABLE
    # unless the promise carries a concrete number (handled in directional fallback).
    "OTHER": {
        "sql": """SELECT NULL::NUMERIC AS actual""",
        "label": "Qualitative (no financial mapping)",
        "reason": "qualitative — no numeric target in promise",
    },
}


def parse_target_quarter(target_str: str) -> tuple | None:
    """Parse various date formats to (fiscal_year, quarter).
    
    Q4FY26 → (2026, 4)       FY26 → (2026, 4)
    H1FY26 → (2026, 2)       H2FY26 → (2026, 4)
    CY2026 → (2026, 4)       Q1CY26 → (2026, 1)
    FY2026 → (2026, 4)
    """
    if not target_str:
        return None
    s = target_str.upper().replace(" ", "").strip()
    try:
        # Q4FY26 or Q1FY2026
        if "Q" in s and "FY" in s:
            q = int(s.split("FY")[0].replace("Q", ""))
            fy = 2000 + int(s.split("FY")[1][:2])
            return (fy, q)
        # H1FY26 / H2FY26
        if s.startswith("H1FY"):
            return (2000 + int(s[4:]), 2)
        if s.startswith("H2FY"):
            return (2000 + int(s[4:]), 4)
        # FY26 / FY2026
        if s.startswith("FY"):
            return (2000 + int(s[2:]), 4)
        # CY2026 / Q1CY26
        if "CY" in s:
            yr = 2000 + int(s.split("CY")[1][:2]) if int(s.split("CY")[1][:2]) < 100 else int(s.split("CY")[1][:4])
            if s.startswith("Q"):
                q = int(s[1])
                return (yr, q)
            return (yr, 4)
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


def fiscal_to_calendar(fy: int, fq: int) -> tuple:
    """Convert fiscal (year, quarter) to calendar (year, month_start).
    Q1FY27 → (2026, 4) [Apr], Q4FY26 → (2026, 1) [Jan]"""
    if fq <= 3:
        return (fy, fq * 3 + 1)
    return (fy, 1)


def has_quarter_passed(target_fy: int, target_fq: int) -> bool:
    """Check if fiscal quarter has passed relative to today."""
    today = date.today()
    cfy, cfq = calendar_to_fiscal(today)
    tc_year, tc_month = fiscal_to_calendar(target_fy, target_fq)
    cc_year, cc_month = fiscal_to_calendar(cfy, cfq)
    # Target quarter ends: start_month + 2
    te_month = tc_month + 2
    te_year = tc_year
    if te_month > 12:
        te_month -= 12
        te_year += 1
    if te_year < cc_year:
        return True
    if te_year == cc_year and te_month < cc_month:
        return True
    return False


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

            if not gtype or gtype not in MAPPING:
                return self._store(cur, sid, None, None, "UNABLE_TO_VERIFY",
                                   reason=f"guidance_type {gtype!r} not in verifier MAPPING")

            parsed = parse_target_quarter(tdate_str or "")
            if not parsed:
                parsed = self._latest_fiscal_quarter(cur, sym)

            fy, fq = parsed
            if not has_quarter_passed(fy, fq):
                return self._store(cur, sid, fy, fq, "PENDING")

            sql = MAPPING[gtype]["sql"]
            default_reason = MAPPING[gtype].get("reason")

            if gtype == "REVENUE_GROWTH":
                cur.execute(sql, (sym, fy, fq, sym, fy, fq))
            else:
                cur.execute(sql, (sym, fy, fq))

            r = cur.fetchone()
            if not r:
                return self._store(cur, sid, fy, fq, "UNABLE_TO_VERIFY",
                                   reason=default_reason or "no financial data for target quarter")

            actual = r[0] if isinstance(r, (list, tuple)) else list(r.values())[0]
            if actual is None:
                # Capacity-style types return NULL by design — record with the
                # type-specific reason so the UI can show *why*.
                if default_reason:
                    return self._store(cur, sid, fy, fq, "UNABLE_TO_VERIFY",
                                       reason=default_reason, actual=None)
                return self._store(cur, sid, fy, fq, "UNABLE_TO_VERIFY",
                                   reason="no financial data for target quarter", actual=None)

            # Safe variance: handle None/missing targets, percentage vs absolute
            try:
                target_f = float(target) if target is not None else None
            except (TypeError, ValueError):
                target_f = None

            if target_f is None or target_f == 0:
                # No numeric target — directional fallback for REVENUE_GROWTH,
                # UNABLE for everything else (with the type-specific reason).
                if gtype == "REVENUE_GROWTH":
                    # Directional: positive YoY = PARTIAL ("grew, even if not by stated number");
                    # negative = MISSED; exactly zero = PARTIAL (flat)
                    actual_pct = float(actual)
                    if actual_pct > 0:
                        status = "PARTIAL"
                    elif actual_pct < 0:
                        status = "MISSED"
                    else:
                        status = "PARTIAL"
                    variance = actual_pct  # store the actual YoY as variance
                    return self._store(cur, sid, fy, fq, status, actual, variance,
                                       reason="directional-only — evaluated YoY direction")
                if default_reason:
                    return self._store(cur, sid, fy, fq, "UNABLE_TO_VERIFY",
                                       reason=default_reason, actual=actual)
                return self._store(cur, sid, fy, fq, "UNABLE_TO_VERIFY",
                                   reason="no numeric target in promise", actual=actual)

            actual_f = float(actual) if actual is not None else None
            if actual_f is None:
                return self._store(cur, sid, fy, fq, "UNABLE_TO_VERIFY",
                                   reason="actual value unavailable", actual=None)

            variance = ((actual_f - target_f) / abs(target_f)) * 100

            # Thresholds adjusted for % targets: margin promises within 2pp considered achieved
            if gtype == "MARGIN":
                # For margin: check absolute pp difference
                abs_diff = abs(actual_f - target_f)
                if abs_diff <= 2.0:
                    status = "ACHIEVED"
                elif abs_diff <= 4.0:
                    status = "PARTIAL"
                else:
                    status = "MISSED"
            else:
                # For revenue/growth: use percentage variance
                if abs(variance) <= 10:
                    status = "ACHIEVED"
                elif abs(variance) <= 25:
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

    def _store(self, cur, gid, fy, fq, status, actual=None, variance=None, reason=None):
        # Only persist the reason when the status is UNABLE_TO_VERIFY — otherwise
        # it's noise. Pass it through anyway so the SQL stays uniform.
        try:
            cur.execute(
                """INSERT INTO public.guidance_verification
                   (guidance_id, checked_fiscal_year, checked_fiscal_quarter,
                    actual_value, status, variance_pct, unable_reason)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (guidance_id, checked_fiscal_year, checked_fiscal_quarter)
                   DO UPDATE SET actual_value=EXCLUDED.actual_value,
                                 status=EXCLUDED.status,
                                 variance_pct=EXCLUDED.variance_pct,
                                 unable_reason=EXCLUDED.unable_reason,
                                 verified_at=NOW()""",
                (gid, fy, fq, actual, status, variance,
                 reason if status == "UNABLE_TO_VERIFY" else None),
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

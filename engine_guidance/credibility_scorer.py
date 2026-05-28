"""
Credibility Scorer — aggregates management guidance accuracy per company.

Usage:
    python3 -m engine_guidance.credibility_scorer --symbol TCS
    python3 -m engine_guidance.credibility_scorer --top 10
"""

import logging
from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("credibility_scorer")


def _get(row, i):
    return row[i] if isinstance(row, (list, tuple)) else list(row.values())[i]


class CredibilityScorer:
    def compute_score(self, symbol: str) -> dict:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT COUNT(*) AS total,
                   SUM(CASE WHEN v.status='ACHIEVED' THEN 1 ELSE 0 END) AS achieved,
                   SUM(CASE WHEN v.status='MISSED' THEN 1 ELSE 0 END) AS missed,
                   SUM(CASE WHEN v.status='PARTIAL' THEN 1 ELSE 0 END) AS partial,
                   AVG(CASE WHEN v.status='MISSED' THEN ABS(v.variance_pct) ELSE NULL END) AS avg_miss
                   FROM guidance_verification v
                   JOIN management_guidance g ON v.guidance_id=g.id
                   WHERE g.symbol=%s AND v.status IN ('ACHIEVED','MISSED','PARTIAL')""",
                (symbol.upper(),),
            )
            row = cur.fetchone()
            if not row:
                return {"symbol": symbol, "total_promises": 0}
            total = int(_get(row, 0) or 0)
            if total == 0:
                return {"symbol": symbol, "total_promises": 0}
            achieved = int(_get(row, 1) or 0)
            missed = int(_get(row, 2) or 0)
            partial = int(_get(row, 3) or 0)
            avg_miss = float(_get(row, 4)) if _get(row, 4) else None
            effective = achieved + (partial * 0.5)
            accuracy = (effective / total) * 100
            trend = self._compute_trend(cur, symbol)

            cur.execute(
                """INSERT INTO management_credibility_scores
                   (symbol,total_promises,achieved_count,missed_count,accuracy_pct,avg_variance_pct,trend)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT(symbol) DO UPDATE SET
                   total_promises=EXCLUDED.total_promises,achieved_count=EXCLUDED.achieved_count,
                   missed_count=EXCLUDED.missed_count,accuracy_pct=EXCLUDED.accuracy_pct,
                   avg_variance_pct=EXCLUDED.avg_variance_pct,trend=EXCLUDED.trend,last_updated=NOW()""",
                (symbol, total, achieved, missed, round(accuracy, 2),
                 round(avg_miss, 2) if avg_miss else None, trend),
            )
            conn.commit()
            logger.info(f"{symbol}: {accuracy:.1f}% ({achieved}/{total}) — {trend}")
            return {"symbol": symbol, "total_promises": total, "achieved": achieved,
                    "missed": missed, "accuracy_pct": round(accuracy, 2),
                    "avg_variance_pct": round(avg_miss, 2) if avg_miss else None, "trend": trend}
        finally:
            conn.close()

    def _compute_trend(self, cur, symbol):
        try:
            cur.execute(
                """WITH ranked AS (
                    SELECT v.status, ROW_NUMBER() OVER (
                        ORDER BY v.checked_fiscal_year DESC, v.checked_fiscal_quarter DESC) rn
                    FROM guidance_verification v JOIN management_guidance g ON v.guidance_id=g.id
                    WHERE g.symbol=%s AND v.status IN ('ACHIEVED','MISSED','PARTIAL'))
                SELECT SUM(CASE WHEN rn<=4 AND status='ACHIEVED' THEN 1
                    WHEN rn<=4 AND status='PARTIAL' THEN 0.5 ELSE 0 END)::FLOAT
                    / NULLIF(SUM(CASE WHEN rn<=4 THEN 1 ELSE 0 END),0) recent,
                    SUM(CASE WHEN rn>4 AND rn<=8 AND status='ACHIEVED' THEN 1
                    WHEN rn>4 AND rn<=8 AND status='PARTIAL' THEN 0.5 ELSE 0 END)::FLOAT
                    / NULLIF(SUM(CASE WHEN rn>4 AND rn<=8 THEN 1 ELSE 0 END),0) prior
                FROM ranked""", (symbol,))
            row = cur.fetchone()
            if not row: return "INSUFFICIENT_DATA"
            recent, prior = _get(row, 0), _get(row, 1)
            if recent is None or prior is None: return "INSUFFICIENT_DATA"
            if recent > prior * 1.1: return "IMPROVING"
            if recent < prior * 0.9: return "DETERIORATING"
            return "STABLE"
        except Exception:
            return "INSUFFICIENT_DATA"

    def get_leaderboard(self, limit=20, worst=False):
        conn = get_connection()
        try:
            cur = conn.cursor()
            order = "ASC" if worst else "DESC"
            cur.execute(f"SELECT * FROM management_credibility_scores WHERE total_promises>=3 ORDER BY accuracy_pct {order} LIMIT %s", (limit,))
            return cur.fetchall()
        finally:
            conn.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", "-s")
    ap.add_argument("--top", type=int)
    ap.add_argument("--worst", type=int)
    args = ap.parse_args()
    scorer = CredibilityScorer()
    if args.symbol:
        r = scorer.compute_score(args.symbol)
        if r['total_promises'] == 0:
            print(f"\n{args.symbol}: No verifiable promises yet — need more quarterly data")
        else:
            print(f"\n{args.symbol}: {r['accuracy_pct']}% ({r['achieved']}/{r['total_promises']}) — {r['trend']}")
    if args.top:
        print(f"\n=== Top {args.top} Most Credible ===")
        for row in scorer.get_leaderboard(args.top):
            s = row if isinstance(row, dict) else {"symbol": row[0], "accuracy_pct": row[4], "total_promises": row[1], "achieved_count": row[2], "trend": row[6]}
            print(f"  {s['symbol']:15s} {s['accuracy_pct']:5.1f}% ({s['achieved_count']}/{s['total_promises']}) {s['trend']}")
    if args.worst:
        print(f"\n=== Worst {args.worst} Offenders ===")
        for row in scorer.get_leaderboard(args.worst, worst=True):
            s = row if isinstance(row, dict) else {"symbol": row[0], "accuracy_pct": row[4], "total_promises": row[1], "missed_count": row[3], "trend": row[6]}
            print(f"  {s['symbol']:15s} {s['accuracy_pct']:5.1f}% ({s['missed_count']} missed) {s['trend']}")

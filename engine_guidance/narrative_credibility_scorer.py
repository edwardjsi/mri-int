"""
Narrative Credibility Scorer — aggregates management credibility from the
iterative narrative timeline (NOT from external financial verification).

The OLD scorer (credibility_scorer.py) computes accuracy_pct from
guidance_verification against aae_quarterly_financials — only 51
actionable signals in the entire universe, and 87.8% of those are
UNABLE_TO_VERIFY.

The NEW scorer reads from management_narrative_timeline (built by
narrative_tracer.py) where management's own later statements ARE the
verification. 796 actionable signals across 140 companies — 15× more
data, with quote verification to defend against hallucination.

Per-promise contribution (0-100):
  FULFILLED             100
  REVISED_UP             95  (target lifted and delivered)
  ON_TRACK               75  (good standing but unproven)
  PARTIALLY_FULFILLED    60
  REVISED_DOWN           35  (target cut = effectively partial miss)
  MISSED                  0
  PENDING / NEW        null  (no signal yet — excluded from score)

Quote-verification discount: if quote_verified = false, ×0.7

Trajectory: (REVISED_UP - REVISED_DOWN) / actionable_promises
  positive = IMPROVING, negative = DETERIORATING, ~0 = STABLE

Lag: consecutive MISSED starting from most recent verified quarter.

Usage:
    python3 -m engine_guidance.narrative_credibility_scorer --symbol CGCL
    python3 -m engine_guidance.narrative_credibility_scorer --all
"""
from __future__ import annotations

import argparse
import logging
from datetime import date
from typing import Optional

from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("narrative_credibility")


# Status -> base score contribution (None = exclude from aggregate)
STATUS_SCORES = {
    "FULFILLED": 100.0,
    "REVISED_UP": 95.0,
    "ON_TRACK": 75.0,
    "PARTIALLY_FULFILLED": 60.0,
    "REVISED_DOWN": 35.0,
    "MISSED": 0.0,
    "PENDING": None,
    "NEW": None,
}

UNVERIFIED_DISCOUNT = 0.7

# Zone thresholds (kept compatible with old scorer)
ZONE_WATCHING = "WATCHING"
ZONE_ADD     = "ADD ZONE"
ZONE_HOLD    = "HOLD ZONE"
ZONE_REDUCE  = "REDUCE ZONE"
ZONE_BROKEN  = "THESIS BROKEN"


def _status_to_score(status: str, quote_verified: bool) -> Optional[float]:
    base = STATUS_SCORES.get(status)
    if base is None:
        return None
    if not quote_verified:
        base = base * UNVERIFIED_DISCOUNT
    return base


def _zone_for(score: Optional[float], trend: str, n_actionable: int) -> str:
    if n_actionable < 3:
        return ZONE_WATCHING
    if score is None:
        return ZONE_WATCHING
    if score >= 75:
        return ZONE_ADD if trend in ("IMPROVING", "STABLE", "INSUFFICIENT_DATA") else ZONE_HOLD
    if score >= 60:
        return ZONE_HOLD
    if score >= 40:
        return ZONE_REDUCE
    return ZONE_BROKEN


def _compute_trajectory(revised_up: int, revised_down: int, n_actionable: int) -> str:
    if n_actionable < 3:
        return "INSUFFICIENT_DATA"
    up_ratio = revised_up / n_actionable
    down_ratio = revised_down / n_actionable
    net = up_ratio - down_ratio
    if net > 0.10:
        return "IMPROVING"
    if net < -0.10:
        return "DETERIORATING"
    return "STABLE"


def _compute_lag(status_by_quarter: dict) -> tuple[int, float]:
    """Consecutive MISSED count from the latest quarter backward.
    Returns (consecutive_miss_quarters, lag_score 0-100).
    """
    if not status_by_quarter:
        return 0, 0.0
    quarters_sorted = sorted(status_by_quarter.keys(), reverse=True)
    streak = 0
    total_scored = sum(
        1 for q in quarters_sorted
        if status_by_quarter[q] in ("FULFILLED", "MISSED", "PARTIALLY_FULFILLED")
    )
    for q in quarters_sorted:
        s = status_by_quarter[q]
        if s == "MISSED":
            streak += 1
        elif s in ("FULFILLED", "PARTIALLY_FULFILLED"):
            break
        # ON_TRACK / REVISED_* / PENDING / NEW — don't break or extend streak
    lag_score = (streak / total_scored) * 100 if total_scored else 0.0
    return streak, round(lag_score, 2)


class NarrativeCredibilityScorer:
    def compute_score(self, symbol: str) -> dict:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT promise_key, current_status, current_quarter,
                          quote_verified, status_by_quarter,
                          evidence_by_quarter, first_seen_quarter,
                          current_evidence_quote, guidance_text
                   FROM management_narrative_timeline
                   WHERE symbol = %s""",
                (symbol.upper(),),
            )
            rows = cur.fetchall()
            if not rows:
                return {"symbol": symbol.upper(), "total_promises": 0,
                        "actionable_promises": 0, "score": None,
                        "verdict": ZONE_WATCHING}

            # ── Per-promise scoring ────────────────────────────────
            scored = []           # (score, status, promise_key)
            counts = {"FULFILLED": 0, "ON_TRACK": 0, "PARTIALLY_FULFILLED": 0,
                      "REVISED_UP": 0, "REVISED_DOWN": 0, "MISSED": 0,
                      "PENDING": 0, "NEW": 0}
            unverified_count = 0
            for r in rows:
                status = r["current_status"]
                counts[status] = counts.get(status, 0) + 1
                score = _status_to_score(status, r["quote_verified"])
                if score is None:
                    continue
                if not r["quote_verified"]:
                    unverified_count += 1
                scored.append((score, status, r["promise_key"]))

            n_actionable = len(scored)
            n_total = len(rows)
            score = round(sum(s for s, _, _ in scored) / n_actionable, 2) if n_actionable else None

            # ── Trajectory ──────────────────────────────────────────
            trend = _compute_trajectory(counts["REVISED_UP"], counts["REVISED_DOWN"], n_actionable)

            # ── Lag (from the latest symbol's most recent quarter across all promises) ──
            # Aggregate status_by_quarter across all promises to find the latest quarter
            latest_q = None
            for r in rows:
                sbq = r["status_by_quarter"] or {}
                if not sbq:
                    continue
                q = max(sbq.keys())
                if latest_q is None or q > latest_q:
                    latest_q = q
            # Build a "consensus per quarter" by aggregating the symbol's statuses
            # for the purpose of lag (use the latest quarter from current_status as anchor)
            # Simpler: walk all promises sorted by current_quarter, count consecutive misses
            all_quarters: dict[str, list[str]] = {}
            for r in rows:
                sbq = r["status_by_quarter"] or {}
                for q, s in sbq.items():
                    all_quarters.setdefault(q, []).append(s)
            consensus_by_q = {q: _consensus_status(slist) for q, slist in all_quarters.items()}
            consecutive_miss, lag_score = _compute_lag(consensus_by_q)

            # ── Verdict zone ────────────────────────────────────────
            new_verdict = _zone_for(score, trend, n_actionable)

            # ── Verdict flip detection ──────────────────────────────
            cur.execute(
                "SELECT current_verdict, previous_verdict FROM management_credibility_scores WHERE symbol=%s",
                (symbol.upper(),),
            )
            stored = cur.fetchone()
            stored_current = stored["current_verdict"] if stored else None
            stored_previous = stored["previous_verdict"] if stored else None
            new_previous = stored_current
            verdict_flipped = stored_current is not None and stored_current != new_verdict
            new_flip_date = None
            if verdict_flipped:
                new_flip_date = date.today()

            # ── Persist ─────────────────────────────────────────────
            cur.execute(
                """INSERT INTO management_credibility_scores
                   (symbol, total_promises, achieved_count, missed_count,
                    accuracy_pct, avg_variance_pct, trend,
                    consecutive_miss_quarters, lag_score, last_verdict_flip,
                    current_verdict, previous_verdict, last_updated)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                   ON CONFLICT(symbol) DO UPDATE SET
                     total_promises = EXCLUDED.total_promises,
                     achieved_count = EXCLUDED.achieved_count,
                     missed_count = EXCLUDED.missed_count,
                     accuracy_pct = EXCLUDED.accuracy_pct,
                     avg_variance_pct = EXCLUDED.avg_variance_pct,
                     trend = EXCLUDED.trend,
                     consecutive_miss_quarters = EXCLUDED.consecutive_miss_quarters,
                     lag_score = EXCLUDED.lag_score,
                     last_verdict_flip = EXCLUDED.last_verdict_flip,
                     current_verdict = EXCLUDED.current_verdict,
                     previous_verdict = EXCLUDED.previous_verdict,
                     last_updated = NOW()""",
                (symbol.upper(), n_total,
                 counts.get("FULFILLED", 0),
                 counts.get("MISSED", 0),
                 score, None, trend,
                 consecutive_miss, lag_score, new_flip_date,
                 new_verdict, new_previous),
            )
            conn.commit()

            return {
                "symbol": symbol.upper(),
                "total_promises": n_total,
                "actionable_promises": n_actionable,
                "score": score,
                "counts": counts,
                "unverified_count": unverified_count,
                "trend": trend,
                "current_verdict": new_verdict,
                "previous_verdict": new_previous,
                "verdict_flipped": bool(verdict_flipped),
                "consecutive_miss_quarters": consecutive_miss,
                "lag_score": lag_score,
                "last_verdict_flip": str(new_flip_date) if new_flip_date else None,
            }
        finally:
            conn.close()


def _consensus_status(statuses: list[str]) -> str:
    """Pick the most actionable status in a quarter, preferring negative.
    Used for lag calculation."""
    priority = ["MISSED", "REVISED_DOWN", "PARTIALLY_FULFILLED",
                "FULFILLED", "REVISED_UP", "ON_TRACK", "PENDING", "NEW"]
    seen = set(statuses)
    for p in priority:
        if p in seen:
            return p
    return "PENDING"


def get_leaderboard(limit: int = 20, worst: bool = False) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()
        order = "ASC" if worst else "DESC"
        cur.execute(
            f"""SELECT symbol, total_promises, accuracy_pct, trend,
                       current_verdict, consecutive_miss_quarters, lag_score
                FROM management_credibility_scores
                WHERE total_promises >= 3 AND accuracy_pct IS NOT NULL
                ORDER BY accuracy_pct {order}
                LIMIT %s""",
            (limit,),
        )
        cols = ["symbol", "total_promises", "accuracy_pct", "trend",
                "current_verdict", "consecutive_miss_quarters", "lag_score"]
        return [dict(zip(cols, [r[c] for c in cols])) for r in cur.fetchall()]
    finally:
        conn.close()


# ── CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", "-s")
    ap.add_argument("--all", action="store_true",
                    help="Score every symbol in management_narrative_timeline")
    ap.add_argument("--top", type=int)
    ap.add_argument("--worst", type=int)
    args = ap.parse_args()

    scorer = NarrativeCredibilityScorer()

    if args.all:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT symbol FROM management_narrative_timeline ORDER BY symbol")
            symbols = [r["symbol"] for r in cur.fetchall()]
        finally:
            conn.close()
        print(f"Scoring {len(symbols)} symbols...")
        for i, sym in enumerate(symbols, 1):
            try:
                r = scorer.compute_score(sym)
                print(f"  [{i}/{len(symbols)}] {sym:<12} score={r.get('score')} verdict={r.get('current_verdict')} trend={r.get('trend')}")
            except Exception as e:
                print(f"  [{i}/{len(symbols)}] {sym:<12} FAILED: {e}")
    elif args.symbol:
        r = scorer.compute_score(args.symbol)
        print(f"\n=== {r['symbol']} ===")
        print(f"  Score: {r.get('score')}")
        print(f"  Verdict: {r.get('current_verdict')}")
        print(f"  Trend: {r.get('trend')}")
        print(f"  Total promises: {r.get('total_promises')}")
        print(f"  Actionable: {r.get('actionable_promises')}")
        print(f"  Counts: {r.get('counts')}")
        print(f"  Consecutive miss quarters: {r.get('consecutive_miss_quarters')}")
        print(f"  Lag score: {r.get('lag_score')}")
        print(f"  Verdict flipped: {r.get('verdict_flipped')}")
    elif args.top:
        for r in get_leaderboard(args.top, worst=False):
            print(f"  {r['symbol']:<12} score={r['accuracy_pct']:>6}  "
                  f"verdict={r['current_verdict']:<14} trend={r['trend']:<18} "
                  f"lag={r['consecutive_miss_quarters']}q")
    elif args.worst:
        for r in get_leaderboard(args.worst, worst=True):
            print(f"  {r['symbol']:<12} score={r['accuracy_pct']:>6}  "
                  f"verdict={r['current_verdict']:<14} trend={r['trend']:<18} "
                  f"lag={r['consecutive_miss_quarters']}q")
    else:
        ap.print_help()

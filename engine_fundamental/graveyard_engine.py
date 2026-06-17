import logging
from engine_core.db import get_connection, fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_credibility(symbol: str) -> dict | None:
    """Read the narrative-timeline-based credibility row for a symbol.

    Returns a flat dict of the columns that drive graveyard decisions,
    or None if no row exists yet (fresh symbol / never scored).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT accuracy_pct, total_promises, missed_count,
                      trend, current_verdict, previous_verdict,
                      consecutive_miss_quarters, lag_score, last_verdict_flip
               FROM management_credibility_scores WHERE symbol = %s""",
            (symbol.upper(),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "score": float(row["accuracy_pct"]) if row["accuracy_pct"] is not None else None,
            "total_promises": int(row["total_promises"] or 0),
            "missed_count": int(row["missed_count"] or 0),
            "trend": row["trend"] or "INSUFFICIENT_DATA",
            "verdict": row["current_verdict"] or "WATCHING",
            "previous_verdict": row["previous_verdict"],
            "consecutive_miss_quarters": int(row["consecutive_miss_quarters"] or 0),
            "lag_score": float(row["lag_score"]) if row["lag_score"] is not None else 0.0,
            "last_verdict_flip": row["last_verdict_flip"],
        }
    finally:
        conn.close()


class GraveyardEngine:
    """
    AAE V3 Forensic Feedback Loop (Layer 7).
    Identifies 'False Positives' and applies penalties to prevent recurring errors.

    AAE × Management Integrity (Phase 2, 2026-06-17):
    Adds two credibility-driven rules *before* the existing manual-burial check:

      1. AUTO-BURY:    consecutive_miss_quarters >= 4 AND score < 40
                       → write to aae_graveyard + return -30 penalty
      2. SOFT PENALTY: consecutive_miss_quarters >= 2
                       → return -10 penalty, NO burial

    Manual burial (Rule 3) is preserved and takes precedence: if a symbol is
    already in aae_graveyard for any reason, auto-bury will NOT overwrite
    the human-set reason_for_death. Conservative default — a recovering
    manager is not silently un-buried; only manual intervention can revive.
    """

    # Phase 2 thresholds — kept as class constants so they're easy to tune.
    AUTO_BURY_MIN_CONSECUTIVE_MISS = 4   # quarters of unbroken misses
    AUTO_BURY_MAX_SCORE = 40             # accuracy_pct ceiling for auto-bury
    SOFT_PENALTY_MIN_CONSECUTIVE_MISS = 2  # quarters of unbroken misses
    HARD_PENALTY = 30                    # applied on burial
    SOFT_PENALTY = 10                    # applied on lag streak

    def __init__(self, symbol):
        self.symbol = symbol.upper()

    def check_burial_status(self):
        """
        Check if the symbol is in the Graveyard.
        """
        query = "SELECT * FROM aae_graveyard WHERE symbol = %s"
        df = fetch_df(query, (self.symbol,))
        if df is not None and not df.empty:
            return df.iloc[0]
        return None

    def evaluate_penalty(self):
        """
        Return a forensic penalty score and reasons.

        Decision order (Phase 2):
            1. Manual burial? → preserve existing reason, return HARD penalty
            2. Auto-bury rule? → write to graveyard + return HARD penalty
            3. Soft lag penalty? → return SOFT penalty (no DB write)
            4. Otherwise → no penalty

        The returned dict includes a `credibility` snapshot for the
        orchestrator / UI to inspect without a second DB roundtrip.
        """
        cred = fetch_credibility(self.symbol)

        # Rule 3 (existing, takes precedence to preserve human-set burials)
        burial = self.check_burial_status()
        if burial is not None:
            return {
                "penalty": self.HARD_PENALTY,
                "reason": (
                    f"FORENSIC REJECTION: Previously buried on "
                    f"{burial['date_buried']} ({burial['reason_for_death']})"
                ),
                "rule": "MANUAL_BURIAL",
                "credibility": cred,
            }

        # Rule 1: auto-bury on credibility collapse
        if cred and cred["score"] is not None:
            if (cred["consecutive_miss_quarters"] >= self.AUTO_BURY_MIN_CONSECUTIVE_MISS
                    and cred["score"] < self.AUTO_BURY_MAX_SCORE):
                cons = cred["consecutive_miss_quarters"]
                score = cred["score"]
                verdict = cred["verdict"]
                reason = (
                    f"AUTO-BURIED: {cons} consecutive missed quarters + "
                    f"{score:.0f}/100 credibility ({verdict})"
                )
                self.bury_symbol(
                    self.symbol,
                    reason=reason,
                    score=score,
                    auto=True,
                )
                logger.warning(
                    f"Auto-buried {self.symbol}: {cons}Q miss streak + "
                    f"{score:.0f}/100 credibility"
                )
                return {
                    "penalty": self.HARD_PENALTY,
                    "reason": reason,
                    "rule": "AUTO_BURY",
                    "credibility": cred,
                }

        # Rule 2: soft penalty for an emerging lag streak
        if cred and cred["consecutive_miss_quarters"] >= self.SOFT_PENALTY_MIN_CONSECUTIVE_MISS:
            cons = cred["consecutive_miss_quarters"]
            lag = cred["lag_score"]
            return {
                "penalty": self.SOFT_PENALTY,
                "reason": (
                    f"Credibility warning: {cons} consecutive missed quarters "
                    f"(lag score {lag:.0f}/100)"
                ),
                "rule": "SOFT_LAG_PENALTY",
                "credibility": cred,
            }

        return {"penalty": 0, "reason": None, "rule": "NONE", "credibility": cred}

    def bury_symbol(self, symbol, reason, score, auto: bool = False):
        """
        Manually or automatically bury a symbol.

        `auto=True` marks the burial in reason_for_death with an [AUTO] prefix
        so manual reviews can distinguish programmatic vs human burials.
        """
        full_reason = f"[AUTO] {reason}" if auto else reason
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO aae_graveyard (symbol, reason_for_death, score_at_death, date_buried)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (symbol) DO UPDATE SET
                reason_for_death = EXCLUDED.reason_for_death,
                score_at_death = EXCLUDED.score_at_death,
                date_buried = NOW()
        """, (symbol.upper(), full_reason, score))
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Symbol {symbol} has been BURIED in the Graveyard: {full_reason}")

if __name__ == "__main__":
    # Test burial
    # engine = GraveyardEngine("YESBANK")
    # engine.bury_symbol("YESBANK", "Endless equity dilution / Asset Quality lies", 45)
    pass

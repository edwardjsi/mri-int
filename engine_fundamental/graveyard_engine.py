import logging
from engine_core.db import get_connection, fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraveyardEngine:
    """
    AAE V3 Forensic Feedback Loop (Layer 7).
    Identifies 'False Positives' and applies penalties to prevent recurring errors.
    """
    
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
        Return a forensic penalty score and reasons if buried.
        """
        burial = self.check_burial_status()
        if burial is not None:
            penalty = 30 # Hard penalty for failures
            reason = f"FORENSIC REJECTION: Previously buried on {burial['date_buried']} ({burial['reason_for_death']})"
            return {"penalty": penalty, "reason": reason}
        return {"penalty": 0, "reason": None}

    def bury_symbol(self, symbol, reason, score):
        """
        Manually or automatically bury a symbol.
        """
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO aae_graveyard (symbol, reason_for_death, score_at_death, date_buried)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (symbol) DO UPDATE SET
                reason_for_death = EXCLUDED.reason_for_death,
                score_at_death = EXCLUDED.score_at_death,
                date_buried = NOW()
        """, (symbol.upper(), reason, score))
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Symbol {symbol} has been BURIED in the Graveyard: {reason}")

if __name__ == "__main__":
    # Test burial
    # engine = GraveyardEngine("YESBANK")
    # engine.bury_symbol("YESBANK", "Endless equity dilution / Asset Quality lies", 45)
    pass

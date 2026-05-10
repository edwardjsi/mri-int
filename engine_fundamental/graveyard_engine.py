import logging
import json
from engine_core.db import get_connection, fetch_df
from engine_qualitative.extractor import get_openai_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraveyardEngine:
    """
    Analyzes failed AAE signals to refine future scoring weights.
    AAE Phase 4: Feedback Loop.
    """
    
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        self.client = get_openai_client()

    def record_failure(self, failure_type, reason, rerating_score, post_failure_return):
        """
        Record a false positive in the graveyard.
        """
        conn = get_connection()
        cur = conn.cursor()
        
        # 1. Ask GPT to analyze the 'Lessons' if possible
        lessons = {}
        if self.client:
            prompt = f"""
            Analyze the failure of an institutional rerating signal for {self.symbol}.
            Signal Score: {rerating_score}
            Failure Type: {failure_type}
            Post-Signal Return: {post_failure_return}%
            
            Identify 3 likely reasons why this rerating failed (e.g., Value Trap, Creative Accounting, Sector Headwinds).
            Return JSON: {{"lessons": ["reason1", "reason2", "reason3"], "bear_thesis": "..."}}
            """
            try:
                resp = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={ "type": "json_object" }
                )
                lessons = json.loads(resp.choices[0].message.content)
            except:
                pass

        cur.execute("""
            INSERT INTO public.aae_false_positive_graveyard (
                symbol, failure_type, failure_reason, rerating_score, 
                post_failure_return, lessons, bear_thesis
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            self.symbol, failure_type, reason, rerating_score,
            post_failure_return, json.dumps(lessons.get('lessons', [])),
            lessons.get('bear_thesis', '')
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Recorded {self.symbol} in the AAE False Positive Graveyard.")

if __name__ == "__main__":
    # Test recording a mock failure
    eng = GraveyardEngine("YESBANK")
    # eng.record_failure("Value Trap", "Persistent NPA issues ignored by narrative", 85.0, -40.0)

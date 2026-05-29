import os
import json
import logging
from engine_core.db import get_connection, fetch_df
from engine_core.llm_client import get_llm_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NarrativeEngine:
    """
    Analyzes management transcripts to detect structural shifts and narrative divergence.
    AAE Layer 2: Narrative Evolution.
    """
    
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        self.client, self.model = get_llm_client()

    def get_latest_transcript(self):
        query = "SELECT * FROM aae_transcripts WHERE symbol = %s ORDER BY date DESC LIMIT 1"
        return fetch_df(query, (self.symbol,))

    def analyze_transcript(self, text, date, financial_deltas=None):
        if not self.client:
            logger.warning("OpenAI client not available for narrative analysis.")
            return None
            
        prompt = f"""
        Analyze the following earnings call transcript for {self.symbol}.
        Financial Inflections Detected (Deterministic): {json.dumps(financial_deltas)}
        
        Extract:
        1. sentiment_score (0.0-1.0, 0.5 neutral)
        2. key_themes (list of strings)
        3. numeric_divergence (Is management more bullish or cautious than the numbers suggest? -1.0 to +1.0)
        4. ceo_confidence (low|medium|high)
        5. narrative_delta (numeric 0.0-1.0: How much has the story changed since the last quarter?)
        6. summary (2 sentence institutional overview)
        
        Return JSON object with these keys.
        """
        
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an institutional equity analyst specializing in structural business inflections."},
                    {"role": "user", "content": prompt + "\n\nTranscript Snippet:\n" + text[:15000]}
                ],
                temperature=0,
                response_format={ "type": "json_object" }
            )
            analysis = json.loads(resp.choices[0].message.content)
            self.store_analysis(date, analysis)
            return analysis
        except Exception as e:
            logger.error(f"Failed to analyze narrative for {self.symbol}: {e}")
            return None

    def store_analysis(self, date, analysis):
        if not analysis: return
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO public.aae_narrative_intelligence (
                symbol, date, sentiment_score, key_themes, 
                numeric_divergence_score, ceo_confidence_level, 
                summary, narrative_delta
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, date) DO UPDATE SET
                sentiment_score = EXCLUDED.sentiment_score,
                key_themes = EXCLUDED.key_themes,
                numeric_divergence_score = EXCLUDED.numeric_divergence_score,
                ceo_confidence_level = EXCLUDED.ceo_confidence_level,
                summary = EXCLUDED.summary,
                narrative_delta = EXCLUDED.narrative_delta,
                updated_at = NOW()
        """, (
            self.symbol, date, analysis.get('sentiment_score'),
            analysis.get('key_themes'), analysis.get('numeric_divergence'),
            analysis.get('ceo_confidence'), analysis.get('summary'),
            analysis.get('narrative_delta')
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Stored narrative analysis for {self.symbol} on {date}")

if __name__ == "__main__":
    # Mock test
    import datetime
    engine = NarrativeEngine("TCS")
    mock_text = "We are seeing a massive structural shift in AI spending. Our order pipeline is at an all-time high."
    # result = engine.analyze_transcript(mock_text, datetime.date.today())
    # print(result)

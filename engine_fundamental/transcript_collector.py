import logging
import datetime
from engine_core.db import get_connection
from engine_fundamental.narrative_engine import NarrativeEngine
from engine_fundamental.delta_engine import compute_structural_deltas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranscriptCollector:
    """
    AAE V3 Transcript Ingestion Framework.
    Saves transcripts and triggers LLM Narrative Analysis.
    """
    
    def __init__(self):
        pass

    def store_transcript(self, symbol, date, text, source_url=None):
        """
        Store raw transcript in the database.
        """
        conn = get_connection()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                INSERT INTO public.aae_transcripts (symbol, date, source_url, raw_text)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    raw_text = EXCLUDED.raw_text,
                    source_url = EXCLUDED.source_url,
                    processed_at = NOW()
            """, (symbol.upper(), date, source_url, text))
            conn.commit()
            logger.info(f"Successfully stored transcript for {symbol} on {date}")
            
            # Trigger immediate narrative analysis
            self.trigger_analysis(symbol, date, text)
            
        except Exception as e:
            logger.error(f"Failed to store transcript for {symbol}: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()

    def trigger_analysis(self, symbol, date, text):
        """
        Run the Narrative Engine (GPT-4o) on the new transcript.
        """
        logger.info(f"Triggering Narrative Analysis for {symbol}...")
        
        # 1. Fetch deterministic financial deltas to provide context to the LLM
        deltas = compute_structural_deltas(symbol)
        
        # 2. Run LLM Analysis
        engine = NarrativeEngine(symbol)
        analysis = engine.analyze_transcript(text, date, financial_deltas=deltas)
        
        if analysis:
            logger.info(f"Narrative Analysis Complete for {symbol}. Sentiment: {analysis.get('sentiment_score')}")
        else:
            logger.warning(f"Narrative Analysis failed for {symbol}")

if __name__ == "__main__":
    # Test ingestion
    collector = TranscriptCollector()
    # collector.store_transcript("360ONE", "2026-01-15", "Demo transcript text...")

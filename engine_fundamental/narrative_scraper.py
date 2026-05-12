import logging
import json
import datetime
from engine_fundamental.narrative_engine import NarrativeEngine
from engine_core.db import get_connection

logger = logging.getLogger(__name__)

class NarrativeScraper:
    """
    Scrapes concall summaries via web search when official transcripts are missing.
    Bridges the gap for 'reasonably useful' institutional reports.
    """
    
    def __init__(self, symbol, search_tool):
        self.symbol = symbol.upper()
        self.search_tool = search_tool
        self.engine = NarrativeEngine(symbol)

    def fetch_and_analyze(self, quarters=["Q1 FY25", "Q4 FY24"]):
        """
        Search for summaries for the requested quarters and analyze them.
        """
        results = []
        for q in quarters:
            query = f"{self.symbol} concall summary points highlights {q}"
            logger.info(f"[NARRATIVE-SCRAPER] Searching for {query}")
            
            try:
                # Use the provided search tool (this will be the search_web tool)
                search_res = self.search_tool(query=query)
                if not search_res:
                    continue
                
                # The search results text is used as the 'transcript'
                text = str(search_res)
                
                # Mock a date for the quarter (approximation)
                mock_date = self._get_approx_date(q)
                
                # Analyze via AI
                analysis = self.engine.analyze_transcript(text, mock_date)
                if analysis:
                    analysis['quarter'] = q
                    results.append(analysis)
                    logger.info(f"[NARRATIVE-SCRAPER] Successfully analyzed {q} for {self.symbol}")
            except Exception as e:
                logger.error(f"[NARRATIVE-SCRAPER] Failed for {q}: {e}")
                
        return results

    def _get_approx_date(self, quarter):
        """Map quarter string to an approximate date object."""
        year_part = quarter.split("FY")[-1]
        full_year = 2000 + int(year_part)
        
        if "Q1" in quarter: return datetime.date(full_year - 1, 8, 15)
        if "Q2" in quarter: return datetime.date(full_year - 1, 11, 15)
        if "Q3" in quarter: return datetime.date(full_year, 2, 15)
        if "Q4" in quarter: return datetime.date(full_year, 5, 15)
        return datetime.date.today()

def backfill_narrative_for_symbol(symbol, search_tool):
    """Utility function to be called from the API or Orchestrator."""
    scraper = NarrativeScraper(symbol, search_tool)
    return scraper.fetch_and_analyze()

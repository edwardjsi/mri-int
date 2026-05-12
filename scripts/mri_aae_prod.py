import logging
import os
import sys
from engine_fundamental.transcript_discovery import TranscriptDiscoveryAgent
from engine_fundamental.aae_orchestrator import AAEOrchestrator
from engine_fundamental.sector_collector import fetch_and_store_sector_history
from engine_core.db import get_connection, fetch_df
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_aae_production_cycle():
    """
    AAE V3 Production Cycle.
    1. Discovery (Top 50)
    2. Ingestion (of discovered URLs - handled by discovery logic)
    3. Orchestration (Top 20)
    4. Persist to Snapshot
    """
    logger.info("Starting AAE V3 Production Cycle...")
    
    # Step 0: Ingest Sector Index History for Relative Benchmarking
    logger.info("Step 0: Fetching Sector Indices History...")
    fetch_and_store_sector_history()
    
    # Step 1: Identify Candidates for Discovery
    discovery = TranscriptDiscoveryAgent()
    candidates = discovery.get_discovery_candidates(30)
    logger.info(f"Priority Discovery Candidates: {candidates}")
    
    # Note: In production, we would use a scraping/API discovery engine.
    # For now, we rely on the manual discovery demonstration or our discovery class.
    
    # Step 2: Full Scan for Top MRI Symbols
    query = "SELECT symbol FROM stock_scores WHERE total_score > 65 ORDER BY total_score DESC LIMIT 20"
    top_picks_df = fetch_df(query)
    if top_picks_df is None or top_picks_df.empty:
        logger.warning("No high-scoring candidates found for AAE scan.")
        return

    top_picks = top_picks_df['symbol'].tolist()
    logger.info(f"Executing AAE Scan for Top Picks: {top_picks}")
    
    results = []
    for symbol in top_picks:
        try:
            orch = AAEOrchestrator(symbol)
            res = orch.run_full_scan()
            results.append(res)
        except Exception as e:
            logger.error(f"Failed to scan {symbol}: {e}")
            
    # Step 3: Persist results to aae_results_snapshot
    if results:
        conn = get_connection()
        cur = conn.cursor()
        for res in results:
            if res.get('status') == 'ACTIVE':
                cur.execute("""
                    INSERT INTO aae_results_snapshot (symbol, master_score, sector, reasons, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (symbol) DO UPDATE SET
                        master_score = EXCLUDED.master_score,
                        sector = EXCLUDED.sector,
                        reasons = EXCLUDED.reasons,
                        updated_at = NOW()
                """, (
                    res['symbol'],
                    res['master_score'],
                    res['sector'],
                    json.dumps(res.get('reasons', []))
                ))
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Persisted {len(results)} AAE results to snapshot.")

if __name__ == "__main__":
    run_aae_production_cycle()

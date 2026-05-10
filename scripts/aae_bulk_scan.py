import logging
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_fundamental.aae_orchestrator import AAEOrchestrator
from engine_core.db import get_connection, fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_bulk_scan(limit=None):
    """
    AAE V3 Bulk Ingestion Worker.
    Scans the active universe and caches results for the UI.
    """
    # Fetch symbols that have recent technical scores (active universe)
    query = "SELECT DISTINCT symbol FROM stock_scores WHERE date > NOW() - INTERVAL '30 days'"
    if limit:
        query += f" LIMIT {limit}"
        
    symbols_df = fetch_df(query)
    
    if symbols_df is None or symbols_df.empty:
        logger.warning("No active symbols found for AAE scan.")
        return

    symbols = symbols_df['symbol'].tolist()
    logger.info(f"Starting AAE Bulk Scan for {len(symbols)} symbols...")

    conn = get_connection()
    cur = conn.cursor()

    count = 0
    for sym in symbols:
        try:
            orchestrator = AAEOrchestrator(sym)
            res = orchestrator.run_full_scan()
            
            if res.get('status') == 'ACTIVE':
                cur.execute("""
                    INSERT INTO public.aae_results_snapshot (
                        symbol, master_score, sector, valuation_status, 
                        ownership_status, reasons
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol) DO UPDATE SET
                        master_score = EXCLUDED.master_score,
                        sector = EXCLUDED.sector,
                        valuation_status = EXCLUDED.valuation_status,
                        ownership_status = EXCLUDED.ownership_status,
                        reasons = EXCLUDED.reasons,
                        updated_at = NOW()
                """, (
                    sym, res.get('master_score'), res.get('sector'),
                    res.get('valuation_status'), res.get('ownership_status'),
                    json.dumps(res.get('reasons', []))
                ))
            else:
                # If rejected (kill switch), remove from snapshot
                cur.execute("DELETE FROM public.aae_results_snapshot WHERE symbol = %s", (sym,))
                
            conn.commit()
            count += 1
            if count % 10 == 0:
                logger.info(f"Progress: {count}/{len(symbols)}")
                
        except Exception as e:
            logger.error(f"Failed to scan {sym}: {e}")
            conn.rollback()

    cur.close()
    conn.close()
    logger.info(f"AAE Bulk Scan Complete. Processed {count} symbols.")

if __name__ == "__main__":
    # For testing, we can limit to 20 symbols
    run_bulk_scan(limit=20)

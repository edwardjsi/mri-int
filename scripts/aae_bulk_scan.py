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


def persist_scan_result(result, scan_source, conn):
    """
    Persist AAE scan to:
      1. aae_scan_history     — append-only timeline (never overwritten)
      2. aae_results_snapshot  — latest-state cache (upserted)
    """
    if result.get("status") == "REJECTED":
        return

    sym = result["symbol"]
    cur = conn.cursor()
    try:
        # 1. Append to immutable history
        cur.execute("""
            INSERT INTO public.aae_scan_history (
                symbol, master_score, sector, market_confirmation,
                debate_conviction, risk_summary, reasons, scan_source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            sym,
            result.get("master_score"),
            result.get("sector"),
            result.get("market_confirmation"),
            result.get("debate_conviction"),
            result.get("risk_summary"),
            json.dumps(result.get("reasons", [])),
            scan_source,
        ))

        # 2. Upsert latest snapshot
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
            sym,
            result.get("master_score"),
            result.get("sector"),
            result.get("valuation_status"),
            result.get("ownership_status"),
            json.dumps(result.get("reasons", [])),
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to persist scan for {sym}: {e}")
    finally:
        cur.close()


def run_bulk_scan(limit=None, only_missing=False, missing_file=None):
    """
    AAE V3 Bulk Ingestion Worker.
    Scans the active universe and persists results to history + snapshot.
    If only_missing=True, reads symbols from missing_file CSV (must have 'symbol' column).
    """
    symbols = []

    if only_missing:
        if not missing_file:
            missing_file = "docs/data_richness_audit/missing_aae.csv"
        import csv as csv_mod
        with open(missing_file, newline='') as f:
            reader = csv_mod.DictReader(f)
            symbols = [row["symbol"] for row in reader]
        if limit:
            symbols = symbols[:limit]
        logger.info(f"Only-missing mode: {len(symbols)} symbols from {missing_file}")
    else:
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
    count = 0
    for sym in symbols:
        try:
            orchestrator = AAEOrchestrator(sym)
            res = orchestrator.run_full_scan()
            persist_scan_result(res, "PIPELINE", conn)

            if res.get('status') == 'REJECTED':
                cur = conn.cursor()
                cur.execute("DELETE FROM public.aae_results_snapshot WHERE symbol = %s", (sym,))
                conn.commit()
                cur.close()

            count += 1
            if count % 10 == 0:
                logger.info(f"Progress: {count}/{len(symbols)}")
        except Exception as e:
            logger.error(f"Failed to scan {sym}: {e}")

    conn.close()
    logger.info(f"AAE Bulk Scan Complete. Processed {count} symbols.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AAE V3 Bulk Scan")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only-missing", action="store_true",
                        help="Scan only symbols in docs/data_richness_audit/missing_aae.csv")
    parser.add_argument("--missing-file", default=None,
                        help="Custom CSV with 'symbol' column (overrides default)")
    args = parser.parse_args()
    run_bulk_scan(limit=args.limit, only_missing=args.only_missing, missing_file=args.missing_file)


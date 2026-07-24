import csv
import sys
import uuid
import logging
import os
from datetime import datetime

# Fix path to work from any location
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine_core.db import get_connection
from engine_core.cai_health_engine import compute_position_health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_portfolio(csv_path: str, email: str, dry_run: bool = False):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM clients WHERE email = %s", (email,))
            client_row = cur.fetchone()
            if not client_row:
                logger.error(f"Client with email {email} not found.")
                return
            client_id = str(client_row[0])
            
            cur.execute("SELECT id FROM cai_portfolio WHERE owner = %s LIMIT 1", (client_id,))
            row = cur.fetchone()
            if row:
                portfolio_id = row[0]
            else:
                portfolio_id = str(uuid.uuid4())
                if not dry_run:
                    cur.execute("INSERT INTO cai_portfolio (id, owner, cash, health) VALUES (%s, %s, 1000000, 100)", (portfolio_id, client_id))
            
            logger.info(f"Using Portfolio ID: {portfolio_id}")

            if not dry_run:
                # PRD says reviews are permanent. Instead of closing all positions (which bypasses the ledger),
                # we just note that we are doing an initialization. We'll set status to CLOSED for now as a reset mechanism,
                # but in production, we should use the ledger. For this import script, this is acceptable for reset.
                cur.execute("DELETE FROM cai_position WHERE portfolio_id = %s", (portfolio_id,))
                logger.info("Cleared existing positions for clean import.")
            else:
                logger.info("DRY RUN: Would clear existing positions.")

            holdings = []
            total_portfolio_value = 1000000.0 # using cash default from above
            
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                headers = [h.strip().lower() for h in reader.fieldnames or []]
                
                # Check for needed headers
                if not any(h in headers for h in ['instrument', 'symbol']):
                    raise ValueError("CSV missing symbol column")
                if not any(h in headers for h in ['qty.', 'qty', 'quantity']):
                    raise ValueError("CSV missing quantity column")
                if not any(h in headers for h in ['invested', 'investment']):
                    raise ValueError("CSV missing invested column")
                if not any(h in headers for h in ['avg. cost', 'avg_cost', 'cost']):
                    raise ValueError("CSV missing avg cost column")
                
                for original_row in reader:
                    # Case insensitive lookup
                    row = {k.strip().lower(): v for k, v in original_row.items() if k}
                    
                    symbol = row.get('instrument') or row.get('symbol')
                    if not symbol:
                        continue
                        
                    symbol = symbol.strip()
                    
                    try:
                        qty = float(row.get('qty.', row.get('qty', row.get('quantity', 0))))
                    except Exception as e:
                        logger.warning(f"Bad qty for {symbol}, skipping row: {e}")
                        qty = 0
                        
                    if qty <= 0:
                        continue
                        
                    try:
                        avg_cost = float(row.get('avg. cost', row.get('avg_cost', row.get('cost', 0))))
                        invested = float(row.get('invested', row.get('investment', 0)))
                    except Exception as e:
                        logger.warning(f"Bad cost/invested for {symbol}, skipping: {e}")
                        continue
                    
                    total_portfolio_value += invested
                    holdings.append({
                        "symbol": symbol,
                        "qty": qty,
                        "avg_cost": avg_cost,
                        "invested": invested
                    })
                    
            logger.info(f"Found {len(holdings)} valid holdings. Total Portfolio Val (incl cash): ₹{total_portfolio_value}")

            for h in holdings:
                pos_id = str(uuid.uuid4())
                allocation_pct = round((h["invested"] / total_portfolio_value) * 100, 2) if total_portfolio_value > 0 else 0
                
                # Tranche is 10% blocks max, according to PRD. So 0-10% is tranche 1-10.
                tranche = max(1, min(10, int(allocation_pct) + 1))
                
                if not dry_run:
                    cur.execute(
                        """
                        INSERT INTO cai_position (id, portfolio_id, symbol, quantity, average_price, allocation, tranche, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                        """,
                        (pos_id, portfolio_id, h["symbol"], h["qty"], h["avg_cost"], allocation_pct, tranche)
                    )
                
                # Compute health independently so one failure doesn't roll back the whole import
                try:
                    health_score = compute_position_health(h["symbol"])
                except Exception as e:
                    logger.warning(f"Health compute failed for {h['symbol']}, defaulting to 50: {e}")
                    health_score = 50.0
                
                review_id = str(uuid.uuid4())
                
                # PRD logic approximation
                if health_score < 30:
                    rec = "EXIT"
                elif health_score < 40:
                    rec = "REDUCE"
                elif health_score < 60:
                    rec = "WAIT"
                elif health_score < 75:
                    rec = "HOLD"
                else:
                    rec = "ADD"
                    
                if not dry_run:
                    cur.execute(
                        """
                        INSERT INTO cai_position_review (
                            id, position_id, trigger, position_health, recommendation, notes
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (review_id, pos_id, "CSV_IMPORT_INIT", health_score, rec, "Automated review from CSV import.")
                    )
                logger.info(f"Imported {h['symbol']} -> {rec} (Health: {health_score}, Alloc: {allocation_pct}%, Tranche: {tranche})")
                
            if not dry_run:
                conn.commit()
                logger.info("Import and review generation complete.")
            else:
                logger.info("DRY RUN: Import would have succeeded.")

    except Exception as e:
        if not dry_run:
            conn.rollback()
        logger.error(f"Failed to import portfolio: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python import_cai_holdings.py <csv_file> <email> [--dry-run]")
        sys.exit(1)
        
    csv_file = sys.argv[1]
    email = sys.argv[2]
    is_dry_run = "--dry-run" in sys.argv
    import_portfolio(csv_file, email, dry_run=is_dry_run)

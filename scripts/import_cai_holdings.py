import csv
import sys
import uuid
import logging
from datetime import datetime

# Adjust path if needed
sys.path.append('/home/immanuels/Desktop/mri-int')
from engine_core.db import get_connection
from engine_core.cai_health_engine import compute_position_health


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_portfolio(csv_path: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Get or create a CAI portfolio for the default client
            client_id = "default_user_1" # In a real app we'd get this from context, let's just use a fixed one or find the one used in the app
            
            # Let's find an existing portfolio or create one
            cur.execute("SELECT id FROM cai_portfolio LIMIT 1")
            row = cur.fetchone()
            if row:
                portfolio_id = row[0]
            else:
                portfolio_id = str(uuid.uuid4())
                cur.execute("INSERT INTO cai_portfolio (id, owner, cash, health) VALUES (%s, %s, 1000000, 100)", (portfolio_id, "default_user"))
            
            logger.info(f"Using Portfolio ID: {portfolio_id}")

            # 2. Close all existing positions (so they don't pollute the new import)
            cur.execute("UPDATE cai_position SET status = 'CLOSED' WHERE portfolio_id = %s", (portfolio_id,))
            logger.info("Closed existing positions.")

            # 3. Read CSV and calculate total invested
            holdings = []
            total_invested = 0.0
            
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                header = next(reader)
                for row in reader:
                    if not row or not row[0].strip():
                        continue
                    
                    symbol = row[0].strip()
                    try:
                        qty = int(row[1])
                    except:
                        qty = 0
                        
                    if qty <= 0:
                        continue
                        
                    avg_cost = float(row[2])
                    invested = float(row[4])
                    
                    total_invested += invested
                    holdings.append({
                        "symbol": symbol,
                        "qty": qty,
                        "avg_cost": avg_cost,
                        "invested": invested
                    })
                    
            logger.info(f"Found {len(holdings)} valid holdings in CSV. Total Invested: ₹{total_invested}")

            # 4. Insert into cai_position and trigger a review for each
            for h in holdings:
                pos_id = str(uuid.uuid4())
                allocation_pct = round((h["invested"] / total_invested) * 100, 2) if total_invested > 0 else 0
                
                # Tranches are roughly 10% per tranche. So 5% = 1 tranche, 15% = 2 tranches? Let's just default to 1 or estimate based on typical 10% limit.
                tranche = max(1, min(10, int(allocation_pct / 2))) # rough estimate
                
                cur.execute(
                    """
                    INSERT INTO cai_position (id, portfolio_id, symbol, quantity, average_price, allocation, tranche, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                    """,
                    (pos_id, portfolio_id, h["symbol"], h["qty"], h["avg_cost"], allocation_pct, tranche)
                )
                
                # Compute health
                health_score = compute_position_health(h["symbol"])
                
                # Automatically move to Review (creating a Position Review)
                review_id = str(uuid.uuid4())
                
                # Dummy logic to set a recommendation based on health
                if health_score < 30:
                    rec = "EXIT"
                elif health_score < 50:
                    rec = "REDUCE"
                elif health_score >= 80:
                    rec = "ADD"
                else:
                    rec = "HOLD"
                    
                cur.execute(
                    """
                    INSERT INTO cai_position_review (
                        id, position_id, trigger, position_health, recommendation, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (review_id, pos_id, "CSV_IMPORT_INIT", health_score, rec, "Automated review from CSV import.")
                )
                logger.info(f"Imported {h['symbol']} and moved to Review ({rec}). Health: {health_score}")
                
            conn.commit()
            logger.info("Import and review generation complete.")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to import portfolio: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "/home/immanuels/Downloads/24July26Holdings.csv"
    import_portfolio(csv_file)

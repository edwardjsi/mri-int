import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine_core.db import get_connection

def seed_missing_workspaces():
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT symbol FROM universe_112co WHERE symbol NOT IN (SELECT symbol FROM ciw_company)')
    missing = cur.fetchall()
    
    if not missing:
        print("No missing workspaces to seed.")
        return
        
    print(f"Seeding workspaces for {len(missing)} companies...")
    for row in missing:
        symbol = row['symbol']
        
        # Insert company
        cur.execute("""
            INSERT INTO ciw_company (symbol, name, sector, portfolio_status, portfolio_allocation, portfolio_avg_cost)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING company_id
        """, (symbol, symbol, 'Unknown', 'Watchlist', 0.0, 0.0))
        company_id = cur.fetchone()['company_id']
        
        # Insert generic thesis node
        cur.execute("""
            INSERT INTO ciw_knowledge_node (company_id, node_type, current_text, confidence, status, history)
            VALUES (%s, 'THESIS', %s, 'MEDIUM', 'ACTIVE', '[]'::jsonb)
        """, (company_id, f"Baseline workspace generated for {symbol}. Awaiting deep AI ingestion from research artifacts."))
        
        # Insert timeline event
        cur.execute("""
            INSERT INTO ciw_timeline_event (company_id, event_type, event_date, summary)
            VALUES (%s, 'SYSTEM', CURRENT_DATE, 'Initial placeholder workspace generated.')
        """, (company_id,))
        
    conn.commit()
    conn.close()
    print("Done!")

if __name__ == '__main__':
    seed_missing_workspaces()

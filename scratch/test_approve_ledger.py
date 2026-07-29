from engine_core.portfolio_os_review_service import PortfolioOsReviewService
from engine_core.db import get_connection

def run_test():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT owner FROM cai_portfolio LIMIT 1")
            row = cur.fetchone()
            if not row:
                print("No CAI portfolios found.")
                return
            client_id = str(row["owner"] if isinstance(row, dict) else row[0])
            
            # Count ledger entries before
            cur.execute("SELECT count(*) FROM cai_decision_ledger")
            count_before = (cur.fetchone()["count"] if isinstance(row, dict) else cur.fetchone()[0])
            print(f"Ledger entries before: {count_before}")
            
    finally:
        conn.close()

    print(f"Testing approve for client: {client_id}")
    service = PortfolioOsReviewService()
    result = service.approve_weekly_review(client_id)
    print("Approve Result:", result)
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Count ledger entries after
            cur.execute("SELECT count(*) FROM cai_decision_ledger")
            count_after = (cur.fetchone()["count"] if isinstance(row, dict) else cur.fetchone()[0])
            print(f"Ledger entries after: {count_after}")
            
            # Show the new entries
            cur.execute("SELECT id, decision_report_id, decision_position_id, execution_status FROM cai_decision_ledger ORDER BY created_at DESC LIMIT 5")
            entries = cur.fetchall()
            print("Latest 5 Ledger Entries:")
            for e in entries:
                print(e)
    finally:
        conn.close()

if __name__ == "__main__":
    run_test()

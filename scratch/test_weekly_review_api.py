from engine_core.portfolio_os_review_service import PortfolioOsReviewService
import json

def run_test():
    # Since we need a client_id, we will query one from the DB
    from engine_core.db import get_connection
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT owner FROM cai_portfolio LIMIT 1")
            row = cur.fetchone()
            if not row:
                print("No CAI portfolios found.")
                return
            if isinstance(row, dict):
                client_id = str(row["owner"])
            else:
                client_id = str(row[0])
    finally:
        conn.close()

    print(f"Testing for client: {client_id}")
    service = PortfolioOsReviewService()
    result = service.generate_weekly_review(client_id)
    
    # Print the resulting JSON
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    run_test()

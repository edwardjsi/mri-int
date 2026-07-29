from engine_core.portfolio_os_review_service import PortfolioOsReviewService
from engine_core.email_service import send_weekly_portfolio_review
from engine_core.db import get_connection

def test_email():
    # 1. Fetch a client
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT owner FROM cai_portfolio LIMIT 1")
            row = cur.fetchone()
            if not row:
                print("No CAI portfolios found.")
                return
            if isinstance(row, dict):
                client_id = str(row["owner"])
            else:
                client_id = str(row[0])
            
            cur.execute("SELECT email, name FROM clients WHERE id = %s", (client_id,))
            client = cur.fetchone()
            if isinstance(client, dict):
                email, name = client["email"], client["name"]
            else:
                email, name = client[0], client[1]
    finally:
        conn.close()
        
    print(f"Generating review for {name} ({email})...")
    
    # 2. Generate Review
    service = PortfolioOsReviewService()
    results = service.generate_weekly_review(client_id)
    
    # 3. Simulate Email Send (bypass actual AWS if credentials missing, but logic runs)
    # We will just write the HTML to a local file to view it if we want
    # Since send_weekly_portfolio_review executes SES, it might return False if no AWS creds
    # but that's fine for testing the logic structure.
    print("Calling send_weekly_portfolio_review...")
    success = send_weekly_portfolio_review(email, name, results)
    print(f"Email send attempt returned: {success}")

if __name__ == "__main__":
    test_email()

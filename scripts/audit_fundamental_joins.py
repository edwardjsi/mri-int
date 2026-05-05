import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def audit_joins():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not found")
        return

    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()

        # 1. Get all symbols in technical scores
        cur.execute("SELECT DISTINCT symbol FROM stock_scores")
        tech_symbols = {r[0] for r in cur.fetchall()}
        print(f"Total Technical Symbols: {len(tech_symbols)}")

        # 2. Get all symbols in fundamental financials
        cur.execute("SELECT DISTINCT symbol FROM fundamental_financials")
        fund_symbols = {r[0] for r in cur.fetchall()}
        print(f"Total Fundamental Symbols: {len(fund_symbols)}")

        # 3. Identify mismatch
        missing_fund = tech_symbols - fund_symbols
        print(f"Symbols with scores but NO fundamental data: {len(missing_fund)}")

        if missing_fund:
            print("\nSample missing fundamental data (first 20):")
            for sym in sorted(list(missing_fund))[:20]:
                # Check if it exists with .NS or .BO
                alt_ns = f"{sym}.NS"
                alt_bo = f"{sym}.BO"
                has_ns = alt_ns in fund_symbols
                has_bo = alt_bo in fund_symbols
                
                status = ""
                if has_ns: status = "(Found with .NS!)"
                elif has_bo: status = "(Found with .BO!)"
                else: status = "(Truly missing)"
                
                print(f" - {sym:<15} {status}")

        # 4. Reverse check: symbols in fundamentals but no scores
        missing_tech = fund_symbols - tech_symbols
        print(f"\nSymbols with fundamental data but NO technical scores: {len(missing_tech)}")
        if missing_tech:
            print("Sample (first 5):", sorted(list(missing_tech))[:5])

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    audit_joins()

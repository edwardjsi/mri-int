import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

def get_db_connection():
    load_dotenv()
    return psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)

def run_sync_demo():
    print("\n=============================================")
    print("      MULTI-ACCOUNT PORTFOLIO SYNC")
    print("=============================================\n")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get Admin ID
    cur.execute("SELECT id FROM clients WHERE is_active = TRUE AND is_admin = TRUE ORDER BY created_at ASC LIMIT 1")
    client_id = str(cur.fetchone()["id"])
    
    # Set up Initial State (22 HSCL Manual, 4 POLYCAB Manual)
    cur.execute("DELETE FROM client_external_holdings WHERE client_id = %s", (client_id,))
    
    # Insert Manual
    cur.execute("""
        INSERT INTO client_external_holdings (client_id, symbol, quantity, avg_cost, source_type, account_source)
        VALUES 
        (%s, 'HSCL', 22, 419.3, 'MANUAL', 'OTHER_ACCOUNT_1'),
        (%s, 'POLYCAB', 4, 6000.0, 'MANUAL', 'OTHER_ACCOUNT_1')
    """, (client_id, client_id))
    
    conn.commit()
    
    # -----------------------------------------------------
    # START ZERODHA SYNC LOGIC
    # -----------------------------------------------------
    
    zerodha_payload = [
        {"symbol": "HSCL", "quantity": 60, "avg_cost": 410.0}
        # Polycab is 0 in Zerodha, so it won't be in the payload
    ]
    
    # 1. Fetch current ZERODHA_MAIN holdings
    cur.execute("SELECT symbol, quantity FROM client_external_holdings WHERE client_id = %s AND account_source = 'ZERODHA_MAIN'", (client_id,))
    old_zerodha = {row["symbol"]: row["quantity"] for row in cur.fetchall()}
    if 'POLYCAB' not in old_zerodha:
        old_zerodha['POLYCAB'] = 0
        
    # 2. Update DB
    for item in zerodha_payload:
        cur.execute("""
            INSERT INTO client_external_holdings (client_id, symbol, quantity, avg_cost, source_type, account_source)
            VALUES (%s, %s, %s, %s, 'ZERODHA_SYNC', 'ZERODHA_MAIN')
            ON CONFLICT (client_id, symbol, account_source)
            DO UPDATE SET quantity = EXCLUDED.quantity, avg_cost = EXCLUDED.avg_cost, updated_at = NOW()
        """, (client_id, item["symbol"], item["quantity"], item["avg_cost"]))
        
    # 3. Find missing ZERODHA_MAIN holdings and delete them
    new_symbols = [item["symbol"] for item in zerodha_payload]
    missing = set(old_zerodha.keys()) - set(new_symbols)
    for sym in missing:
        cur.execute("DELETE FROM client_external_holdings WHERE client_id = %s AND symbol = %s AND account_source = 'ZERODHA_MAIN'", (client_id, sym))
        
    conn.commit()
    
    # -----------------------------------------------------
    # OUTPUT REPORT
    # -----------------------------------------------------
    print("ZERODHA SYNC")
    print("────────────────────────")
    for item in zerodha_payload:
        sym = item["symbol"]
        old_qty = old_zerodha.get(sym, 0)
        status = "ALIGNED" if old_qty == item["quantity"] else f"UPDATED ({old_qty} -> {item['quantity']})"
        print(f"{sym:<10} {old_qty:>4} -> {item['quantity']:<4} {status}")
    for sym in missing:
        print(f"{sym:<10} {old_zerodha[sym]:>4} -> 0    ALIGNED")
        
    print("\nMANUAL HOLDINGS")
    print("────────────────────────")
    cur.execute("SELECT symbol, quantity, account_source FROM client_external_holdings WHERE client_id = %s AND source_type = 'MANUAL'", (client_id,))
    manual_holdings = cur.fetchall()
    for h in manual_holdings:
        print(f"{h['symbol']:<10} {h['quantity']:>4}          PRESERVED")
        
    print("\nTOTAL ECONOMIC HOLDING")
    print("────────────────────────")
    cur.execute("""
        SELECT symbol, SUM(quantity) as quantity 
        FROM client_external_holdings 
        WHERE client_id = %s 
        GROUP BY symbol
        ORDER BY symbol
    """, (client_id,))
    economic_holdings = cur.fetchall()
    for h in economic_holdings:
        print(f"{h['symbol']:<10} {h['quantity']:>4}")
        
    print("\n=============================================")

if __name__ == "__main__":
    run_sync_demo()

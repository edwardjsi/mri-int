import os
import uuid
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Hardcode the correct portfolio
portfolio_id = '90406efc-35b3-4639-831f-9190501e239b'
wrong_portfolio_id = '3380ab9a-1b50-41f3-a6c0-4ea4916b8f1e'

# Delete the wrongly inserted data
print("Cleaning up old mistake...")
cur.execute("DELETE FROM cai_trade_ledger WHERE portfolio_id = %s", (wrong_portfolio_id,))
cur.execute("DELETE FROM cai_position WHERE portfolio_id = %s", (wrong_portfolio_id,))
cur.execute("DELETE FROM cai_portfolio WHERE id = %s", (wrong_portfolio_id,))
print("Cleanup done.")

def insert_ledger_event(portfolio_id, position_id, symbol, event_type, allocation_reason, execution_date, price, quantity):
    event_id = str(uuid.uuid4())
    capital = float(price) * float(quantity) if price and quantity else 0.0
    cur.execute(
        """
        INSERT INTO cai_trade_ledger 
        (id, portfolio_id, position_id, symbol, event_type, allocation_reason, execution_date, price, quantity, capital_allocated)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (event_id, portfolio_id, position_id, symbol, event_type, allocation_reason, execution_date, price, quantity, capital)
    )

csv_data = """Symbol,Date,Quantity,Price,Allocation Reason
AZAD,2026-08-04,8,2354.60,D1_ENTRY
LENSKART,2026-07-27,40,562.75,D1_ENTRY
TORNTPHARM,2026-07-16,6,4988.00,D1_ENTRY
PGEL,2026-07-16,30,620.00,D1_ENTRY
RATEGAIN,2026-07-16,20,976.80,D1_ENTRY
RATEGAIN,2026-08-04,30,979.86,D2_TRANCHE
HSCL,2026-07-20,40,707.85,D1_ENTRY
HSCL,2026-07-20,60,768.20,D2_TRANCHE
DIVISLAB,2026-07-15,3,7322.00,D1_ENTRY
DIVISLAB,2026-07-29,4,7716.50,D2_TRANCHE
IPCALAB,2026-07-14,11,1840.73,D1_ENTRY
IPCALAB,2026-07-16,11,1889.61,D2_TRANCHE
GRANULES,2026-07-10,20,891.30,D1_ENTRY
POONAWALLA,2026-07-01,50,445.25,D1_ENTRY
IKS,2026-07-02,10,1841.95,D1_ENTRY
NAVINFLUOR,2026-07-01,3,7652.00,D1_ENTRY
NEULANDLAB,2026-06-24,2,18458.00,D1_ENTRY
NEULANDLAB,2026-07-01,1,19023.00,D2_TRANCHE
NEULANDLAB,2026-07-29,2,19409.50,D3_TRANCHE
LUPIN,2026-06-22,22,2454.99,D1_ENTRY
WELCORP,2026-07-01,200,1389.31,D1_ENTRY
POLYCAB,2026-07-01,16,9754.50,D1_ENTRY
BSLGOLDETF,2026-07-01,6250,44.10,D1_ENTRY
BHARATFORG,2026-07-20,10,2181.20,D1_ENTRY
SHAILY,2026-08-05,6,3142.40,D1_ENTRY
RADICO,2026-07-20,5,4148.00,D1_ENTRY
LLOYDMET,2026-07-20,10,1914.20,D1_ENTRY
LLOYDMET,2026-07-27,15,2020.20,D2_TRANCHE
SOLARINDS,2026-07-21,1,19000.00,D1_ENTRY"""

lines = csv_data.strip().split('\n')
events = []
for line in lines[1:]:
    parts = line.split(',')
    events.append({
        "symbol": parts[0].strip(),
        "date": parts[1].strip(),
        "quantity": int(parts[2].strip()),
        "price": float(parts[3].strip()),
        "allocation_reason": parts[4].strip()
    })

events.sort(key=lambda x: x["date"])

print("Seeding correctly...")
for event in events:
    symbol = event["symbol"]
    
    cur.execute(
        "SELECT id, quantity, average_price, tranche FROM cai_position WHERE portfolio_id = %s AND symbol = %s AND status = 'ACTIVE'",
        (portfolio_id, symbol)
    )
    pos = cur.fetchone()
    
    if not pos:
        # If it doesn't exist, we skip since we only want to attach ledger events to existing positions, OR we can create it if missing
        pass
    else:
        pos_id = pos["id"]
        # In the actual seed, we don't want to re-accumulate the positions since they are ALREADY inserted with their correct quantities and tranches!
        # Wait, if they are ALREADY fully sized in the database, we JUST need to insert the ledger events!
        # Because the positions table already has the correct `quantity` and `average_price`!
        insert_ledger_event(portfolio_id, pos_id, symbol, "BUY", event["allocation_reason"], event["date"], event["price"], event["quantity"])

conn.commit()
print("Data imported successfully!")

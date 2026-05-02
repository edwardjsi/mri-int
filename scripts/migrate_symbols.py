"""
Migration Script: Normalize Symbols in Fundamental Tables
Strips .NS and .BO suffixes from quality_verdicts and fundamental_financials.
"""
import os
import psycopg2
from engine_core.db import get_connection

def migrate():
    conn = get_connection()
    cur = conn.cursor()
    
    print("Starting symbol normalization migration...")
    
    # 1. Update quality_verdicts
    cur.execute("""
        UPDATE quality_verdicts 
        SET symbol = UPPER(REPLACE(REPLACE(symbol, '.NS', ''), '.BO', ''))
        WHERE symbol LIKE '%.NS' OR symbol LIKE '%.BO'
    """)
    print(f"Updated {cur.rowcount} rows in quality_verdicts.")
    
    # 2. Update quality_verdicts_history
    cur.execute("""
        UPDATE quality_verdicts_history 
        SET symbol = UPPER(REPLACE(REPLACE(symbol, '.NS', ''), '.BO', ''))
        WHERE symbol LIKE '%.NS' OR symbol LIKE '%.BO'
    """)
    print(f"Updated {cur.rowcount} rows in quality_verdicts_history.")
    
    # 3. Update fundamental_financials
    cur.execute("""
        UPDATE fundamental_financials 
        SET symbol = UPPER(REPLACE(REPLACE(symbol, '.NS', ''), '.BO', ''))
        WHERE symbol LIKE '%.NS' OR symbol LIKE '%.BO'
    """)
    print(f"Updated {cur.rowcount} rows in fundamental_financials.")
    
    # 4. Update qil_sources (if any)
    cur.execute("""
        UPDATE qil_sources 
        SET symbol = UPPER(REPLACE(REPLACE(symbol, '.NS', ''), '.BO', ''))
        WHERE symbol LIKE '%.NS' OR symbol LIKE '%.BO'
    """)
    print(f"Updated {cur.rowcount} rows in qil_sources.")

    conn.commit()
    cur.close()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()

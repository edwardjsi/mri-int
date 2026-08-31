from engine_core.db import get_connection

def remove_no_data_stocks():
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT symbol 
        FROM universe_112co 
        WHERE is_active = TRUE
          AND symbol NOT IN (SELECT DISTINCT symbol FROM daily_prices)
    """)
    no_data = cur.fetchall()
    
    if no_data:
        print("Removing stocks with no daily prices data:")
        for row in no_data:
            sym = row['symbol']
            print(sym)
            cur.execute("DELETE FROM universe_112co WHERE symbol = %s", (sym,))
        conn.commit()
        print(f"Removed {len(no_data)} stocks.")
    else:
        print("All active 112co stocks have data.")

if __name__ == "__main__":
    remove_no_data_stocks()

import sys
import os
# Add parent directory to sys.path to find src module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db import get_connection

def vacuum_database():
    """Performs a FULL VACUUM to reclaim space from the 1.3 million deleted rows."""
    print("Connecting to database for maintenance...")
    conn = get_connection()
    # Need to set isolation level to 0 (AUTOCOMMIT) for VACUUM
    conn.set_isolation_level(0)
    cur = conn.cursor()
    
    print("Reclaiming space from daily_prices (VACUUM FULL)... This may take a minute.")
    try:
        cur.execute("VACUUM (FULL, ANALYZE) daily_prices;")
        print("✅ daily_prices shrunk.")
        
        print("Reclaiming space from stock_scores (VACUUM FULL)...")
        cur.execute("VACUUM (FULL, ANALYZE) stock_scores;")
        print("✅ stock_scores shrunk.")
        
        print("\n🎉 Database optimization complete. Check your Neon console; the size should drop significantly soon.")
    except Exception as e:
        print(f"❌ Vacuum failed: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    vacuum_database()

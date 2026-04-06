import sys
import os
from datetime import datetime, timedelta

# Add parent directory to sys.path to find src module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.db import get_connection

def purge_old_data():
    """Removes data older than 2 years from daily_prices and stock_scores."""
    conn = get_connection()
    cur = conn.cursor()
    
    # 2 Year Cutoff
    cutoff_date = (datetime.now() - timedelta(days=730)).date()
    print(f"Purging data older than {cutoff_date}...")
    
    try:
        # 1. Purge daily_prices
        cur.execute("SELECT COUNT(*) FROM daily_prices WHERE date < %s", (cutoff_date,))
        count_prices = cur.fetchone()[0]
        
        if count_prices > 0:
            print(f"Found {count_prices} rows in daily_prices to delete...")
            cur.execute("DELETE FROM daily_prices WHERE date < %s", (cutoff_date,))
            print("Successfully deleted from daily_prices.")
        else:
            print("No old data found in daily_prices.")
            
        # 2. Purge stock_scores
        cur.execute("SELECT COUNT(*) FROM stock_scores WHERE date < %s", (cutoff_date,))
        count_scores = cur.fetchone()[0]
        
        if count_scores > 0:
            print(f"Found {count_scores} rows in stock_scores to delete...")
            cur.execute("DELETE FROM stock_scores WHERE date < %s", (cutoff_date,))
            print("Successfully deleted from stock_scores.")
        else:
            print("No old data found in stock_scores.")
            
        conn.commit()
        print("\n✅ Purge complete and committed.")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error during purge: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    purge_old_data()

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine_core.db import get_connection
from engine_core.model_results_repository import ModelResultRepository
from engine_core.model_runner import ModelRunner
from engine_core.rrg_model import RrgModel
from datetime import date
import time

def main():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM universe_112co")
    symbols = [row['symbol'] for row in cur.fetchall()]
    
    print(f"Running RRG model for {len(symbols)} symbols...")
    
    repo = ModelResultRepository(conn=conn)
    runner = ModelRunner(repository=repo, models=[RrgModel()])
    
    runner.run(symbols, date.today())
    
    conn.commit()
    conn.close()
    
    print("Done! Check RRG page.")

if __name__ == '__main__':
    main()

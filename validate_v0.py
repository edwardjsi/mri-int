import pandas as pd
from engine_core.db import get_connection

def run_full_validation():
    conn = get_connection()
    print("Loading historical reconstructed breakouts...")
    recon_df = pd.read_csv('mri_v0_breakouts.csv')
    recon_df['date'] = pd.to_datetime(recon_df['date'])
    
    # Filter recon to overlapping period (2025-03-01 to end)
    recon_overlap = recon_df[recon_df['date'] >= '2025-03-01'].copy()
    recon_set = set(zip(recon_overlap['symbol'], recon_overlap['date']))
    
    print("Fetching production breakouts from DB (>= 2025-03-01)...")
    query = """
        SELECT symbol, date 
        FROM daily_prices 
        WHERE breakout_state = 'BROKEN_OUT' 
          AND date >= '2025-03-01'
    """
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()
        
    db_set = set((r['symbol'], pd.to_datetime(r['date'])) for r in rows)
    
    total_db = len(db_set)
    total_recon = len(recon_set)
    
    exact_matches = recon_set.intersection(db_set)
    false_positives = recon_set - db_set
    false_negatives = db_set - recon_set
    
    match_pct = (len(exact_matches) / total_db) * 100 if total_db > 0 else 0
    
    print("\\n--- VALIDATION RESULTS ---")
    print(f"Production BROKEN_OUT events (overlapping period): {total_db}")
    print(f"Reconstructed breakout events (overlapping period): {total_recon}")
    print(f"Exact matches: {len(exact_matches)}")
    print(f"False positives (in Recon, not in DB): {len(false_positives)}")
    print(f"False negatives (in DB, not in Recon): {len(false_negatives)}")
    print(f"Match percentage (Matches / DB Events): {match_pct:.2f}%")
    
    print("\\n--- 20 HISTORICAL BREAKOUTS FOR MANUAL VERIFICATION ---")
    sample = recon_df[(recon_df['date'] >= '2015-01-01') & (recon_df['date'] <= '2024-12-31')].sample(20, random_state=42)
    print(sample[['symbol', 'date', 'entry_price', 'regime']].to_string(index=False))

if __name__ == '__main__':
    run_full_validation()

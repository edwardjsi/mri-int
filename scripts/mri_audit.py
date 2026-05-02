"""
MRI Full Audit Script: Verifies Data Population and Pipeline State.
Run this in the production environment to confirm signals, fundamentals, and emails.
"""
import os
from datetime import datetime
from engine_core.db import get_connection

def audit():
    conn = get_connection()
    cur = conn.cursor()
    
    print(f"=== MRI System Audit — {datetime.now()} ===")
    
    # 1. Check Technical Scores (MRI)
    cur.execute("SELECT COUNT(*) AS count, MAX(date) AS max_date FROM stock_scores")
    row = cur.fetchone()
    count = row[0] if isinstance(row, (list, tuple)) else row['count']
    max_date = row[1] if isinstance(row, (list, tuple)) else row['max_date']
    print(f"[Technical] stock_scores: {count} rows. Latest date: {max_date}")
    
    # 2. Check Swing Signals (STEE)
    cur.execute("SELECT COUNT(*) AS count FROM swing_trades WHERE status = 'OPEN'")
    row = cur.fetchone()
    open_trades = row[0] if isinstance(row, (list, tuple)) else row['count']
    print(f"[STEE] Open Swing Trades: {open_trades}")
    
    # 3. Check Fundamental Data
    cur.execute("SELECT COUNT(DISTINCT symbol) AS count FROM quality_verdicts")
    row = cur.fetchone()
    q_stocks = row[0] if isinstance(row, (list, tuple)) else row['count']
    print(f"[Fundamental] Quality Verdicts: {q_stocks} symbols analyzed.")
    
    cur.execute("SELECT COUNT(*) AS count FROM fundamental_financials")
    row = cur.fetchone()
    f_rows = row[0] if isinstance(row, (list, tuple)) else row['count']
    print(f"[Fundamental] Financial History: {f_rows} year-records stored.")
    
    # 4. Check Client Alerts (Email Log)
    # Note: We don't have an email_log table, but we can check action_history for email-related actions
    try:
        cur.execute("SELECT COUNT(*) AS count FROM action_history WHERE action_type LIKE '%email%'")
        row = cur.fetchone()
        emails = row[0] if isinstance(row, (list, tuple)) else row['count']
        print(f"[Pipeline] Email-related actions recorded: {emails}")
    except:
        conn.rollback()
        print("[Pipeline] No action_history table found.")
        
    # 5. Check for today's specific high-quality stocks
    cur.execute("""
        SELECT symbol, score, category 
        FROM quality_verdicts 
        WHERE category IN ('HIGH_QUALITY', 'EARLY_COMPOUNDER') 
        ORDER BY score DESC LIMIT 5
    """)
    rows = cur.fetchall()
    print("\n--- Top Quality Candidates ---")
    for r in rows:
        sym = r[0] if isinstance(r, (list, tuple)) else r['symbol']
        score = r[1] if isinstance(r, (list, tuple)) else r['score']
        cat = r[2] if isinstance(r, (list, tuple)) else r['category']
        print(f"{sym}: {score:.1f} ({cat})")

    conn.close()
    print("\nAudit Complete.")

if __name__ == "__main__":
    audit()

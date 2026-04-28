import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.db import get_connection

def fetch_latest_results(limit=1000):
    conn = get_connection()
    cur = conn.cursor()

    # In our schema, it's 'quality_verdicts' table with 'symbol' column
    cur.execute("""
    SELECT symbol, score, category, created_at
    FROM quality_verdicts
    WHERE created_at >= NOW() - INTERVAL '7 days'
    ORDER BY score DESC
    LIMIT %s
    """, (limit,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def top20(rows):
    return rows[:20]

def format_report(rows):
    lines = []
    lines.append(f"MRI Quality Alpha Weekly Report ({datetime.now().date()})")
    lines.append("="*50)
    lines.append("Top 20 High Quality Candidates (Fundamental Filter):\n")

    for i, row in enumerate(rows, 1):
        # Handle both RealDictRow and tuple
        t = row['symbol'] if isinstance(row, dict) else row[0]
        score = row['score'] if isinstance(row, dict) else row[1]
        cat = row['category'] if isinstance(row, dict) else row[2]
        
        lines.append(f"{i:02d}. {t:<15} | Score: {float(score):>5.1f} | {cat}")

    lines.append("\n" + "="*50)
    lines.append("Confidence: Institutional Grade (7-Agent Deterministic + LLM QIL)")
    
    return "\n".join(lines)

def generate():
    print("Generating Weekly Top-20 Quality Report...")
    rows = fetch_latest_results()
    if not rows:
        print("No results found in the last 7 days. Ensure the pipeline has run.")
        return
        
    top = top20(rows)
    report = format_report(top)

    # Save to outputs directory
    os.makedirs("outputs", exist_ok=True)
    report_path = f"outputs/weekly_quality_report_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(report_path, "w") as f:
        f.write(report)
    
    # Also save as the "latest"
    with open("outputs/weekly_quality_report_latest.txt", "w") as f:
        f.write(report)

    print(f"Report generated: {report_path}")
    print("\n" + report)

if __name__ == "__main__":
    generate()

import sys
import os
sys.path.append(os.getcwd())
try:
    from engine_core.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT MIN(year), MAX(year), COUNT(*) FROM aae_quarterly_financials")
    qf = cur.fetchone()
    print("aae_quarterly_financials (year_min, year_max, count):", qf)
    
    cur.execute("SELECT MIN(fiscal_year), MAX(fiscal_year), COUNT(*) FROM prde_ratios_annual")
    ra = cur.fetchone()
    print("prde_ratios_annual (year_min, year_max, count):", ra)
    
    cur.execute("SELECT MIN(year), MAX(year), COUNT(*) FROM fundamental_financials")
    ff = cur.fetchone()
    print("fundamental_financials (year_min, year_max, count):", ff)
    
except Exception as e:
    print("DB Connection Error:", str(e))

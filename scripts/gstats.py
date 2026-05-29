from engine_core.db import get_connection
c = get_connection()
cur = c.cursor()
cur.execute("SELECT symbol, COUNT(*) as n FROM management_guidance GROUP BY symbol ORDER BY n DESC")
for r in cur.fetchall():
    s = r[0] if isinstance(r,tuple) else r['symbol']
    print(f'{s:15s} {r[1] if isinstance(r,tuple) else r["count"]} stmts')
cur.execute("SELECT * FROM management_credibility_scores")
for r in cur.fetchall():
    print(f'SCORE: {r[0] if isinstance(r,tuple) else r["symbol"]} {(r[4] if isinstance(r,tuple) else r["accuracy_pct"])}%')
c.close()

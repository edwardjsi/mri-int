from engine_core.db import get_connection
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT p.symbol, r.recommendation FROM cai_position p JOIN cai_position_review r ON p.id = r.position_id;")
for row in cur.fetchall():
    print(row)

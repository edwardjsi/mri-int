import json, psycopg2
try:
    with open('api/deps.py') as f:
        pass
    conn = psycopg2.connect(host='localhost', port=5433, dbname='mri', user='mri_dev', password='password')
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol FROM daily_prices WHERE symbol LIKE '%RATE%';")
    print(cur.fetchall())
except Exception as e:
    print(e)

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

with open("migrations/013_cai_trade_ledger.sql", "r") as f:
    sql = f.read()

cur.execute(sql)
conn.commit()

print("Migration applied successfully to Neon DB!")

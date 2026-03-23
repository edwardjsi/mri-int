import argparse
import sys
import os
import pandas as pd

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.db import get_connection

def run_query(query):
    print(f"Executing query: {query}")
    print("-" * 40)
    
    conn = get_connection()
    if not conn:
        print("❌ Failed to connect to the database. Check .env configuration.")
        return
        
    try:
        query_upper = query.strip().upper()
        if query_upper.startswith(("DELETE", "UPDATE", "INSERT", "DROP", "CREATE")):
            cur = conn.cursor()
            cur.execute(query)
            conn.commit()
            print(f"✅ Statement executed successfully. Rows affected: {cur.rowcount}")
            cur.close()
        else:
            # Using pandas for pretty printing the tabular result for SELECT
            df = pd.read_sql_query(query, conn)
            if df.empty:
                print("No rows returned.")
            else:
                print(df.to_markdown(index=False))
                print("-" * 40)
                print(f"Total rows: {len(df)}")
    except Exception as e:
        print(f"❌ Error executing query: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug Database Queries")
    parser.add_argument("--query", type=str, help="SQL query to execute")
    args = parser.parse_args()
    
    if args.query:
        run_query(args.query)
    else:
        print("No query provided. Testing basic connection...")
        conn = get_connection()
        if conn:
            print("✅ Successfully connected to the database!")
            conn.close()
        else:
            print("❌ Connection failed.")

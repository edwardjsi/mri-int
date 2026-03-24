import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load Railway/Neon database URL from .env
load_dotenv()

def check_users():
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("\n--- Registered Users in Database ---")
        cur.execute("SELECT id, email, name, created_at FROM clients")
        users = cur.fetchall()
        
        if not users:
            print("No users found in the database.")
            
        for user in users:
            print(f"Email: {user['email']} | Name: {user['name']} | Created: {user['created_at']}")
            
        print("------------------------------------\n")
        
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_users()

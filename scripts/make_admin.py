import os
import sys
import argparse

# Ensure src modules can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import get_connection

def make_admin(email: str):
    conn = get_connection()
    cur = conn.cursor()
    
    # Self-healing: Ensure column exists
    cur.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
    
    # Check if user exists
    cur.execute("SELECT id, name FROM clients WHERE email = %s", (email,))
    user = cur.fetchone()
    
    if not user:
        print(f"❌ Error: No user found with email '{email}'")
        sys.exit(1)
        
    # Upgrade user
    cur.execute("UPDATE clients SET is_admin = TRUE WHERE email = %s", (email,))
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ Success! User '{user[1]}' ({email}) has been successfully upgraded to an Admin.")
    print("They can now log out and log back in to their dashboard to see the new Admin tab.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote a user to Admin in the MRI platform.")
    parser.add_argument("email", help="The email address of the user to promote.")
    args = parser.parse_args()
    make_admin(args.email)

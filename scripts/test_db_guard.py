import os
import sys

def require_test_db():
    database_url = os.environ.get("DATABASE_URL", "")
    if "ep-bold-mud" in database_url or "neondb" in database_url:
        if os.environ.get("TEST_ALLOW_PROD_DB") != "1":
            print("CRITICAL: Test script attempted to connect to the production Neon database. Aborting to prevent data corruption.")
            print("Use TEST_ALLOW_PROD_DB=1 to override if you are absolutely sure.")
            sys.exit(1)

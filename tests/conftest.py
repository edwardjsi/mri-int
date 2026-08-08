import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def guard_production_db():
    """
    Ensure tests never run against the production database accidentally.
    """
    database_url = os.environ.get("DATABASE_URL", "")
    if "ep-bold-mud" in database_url or "neondb" in database_url:
        if os.environ.get("TEST_ALLOW_PROD_DB") != "1":
            pytest.exit("CRITICAL: Test suite attempted to connect to the production Neon database. Aborting to prevent data corruption.\nUse TEST_ALLOW_PROD_DB=1 to override if you are absolutely sure.")

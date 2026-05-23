"""
Row-Level Security (RLS) migration for MRI tables.

Creates a `client_id` column where missing and enables RLS policies so that
each client can only see their own data. Also creates a tenant admin role
that can see everything.

Run: python -m engine_core.rls_migration
"""

from __future__ import annotations

import os
import logging
import psycopg2
from engine_core.db import get_connection

logger = logging.getLogger(__name__)

# Tables that need RLS. Only perx_reports, aae_scan_history, aae_results_snapshot
# actually have a client_id relationship. Other tables are shared (market data).
RLS_TABLES = [
    "perx_reports",
    "perx_scores",
    "aae_scan_history",
    "aae_results_snapshot",
    "email_log",
]


def _ensure_client_id_column(cur, table: str) -> bool:
    """Add client_id column if it doesn't exist."""
    cur.execute(
        f"""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = '{table}' AND column_name = 'client_id'
        """
    )
    if cur.fetchone():
        return False  # already exists

    logger.info(f"Adding client_id column to {table}")
    cur.execute(f'ALTER TABLE {table} ADD COLUMN client_id UUID')
    return True


def _ensure_rls_enabled(cur, table: str) -> bool:
    """Enable RLS on the table if not already enabled."""
    cur.execute(f"SELECT relrowsecurity FROM pg_class WHERE relname = '{table}'")
    row = cur.fetchone()
    if row and (row[0] if not isinstance(row, dict) else row.get("relrowsecurity")):
        return False  # already enabled

    logger.info(f"Enabling RLS on {table}")
    cur.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    return True


def _drop_existing_policies(cur, table: str):
    """Drop existing policies on the table to avoid conflicts."""
    cur.execute(f"""
        SELECT policyname FROM pg_policies
        WHERE tablename = '{table}'
    """)
    existing = cur.fetchall()
    for row in existing:
        name = row[0] if not isinstance(row, dict) else row.get("policyname")
        if name and "tenant_admin" not in name:
            logger.info(f"  Dropping policy {name} on {table}")
            cur.execute(f"DROP POLICY IF EXISTS {name} ON {table}")


def _create_policies(cur, table: str):
    """Create RLS policies for a table."""
    # Policy 1: Users can only see their own rows
    cur.execute(f"""
        CREATE POLICY user_isolation_{table} ON {table}
        FOR ALL
        USING (client_id = current_setting('app.current_client_id')::UUID)
    """)
    logger.info(f"  Created user_isolation_{table}")

    # Policy 2: Tenant admin can see all rows (for support / super admin)
    try:
        cur.execute(f"""
            CREATE POLICY tenant_admin_access_{table} ON {table}
            FOR ALL
            USING (current_setting('app.tenant_admin') = 'true')
        """)
        logger.info(f"  Created tenant_admin_access_{table}")
    except Exception:
        logger.warning("Could not create tenant admin policy (likely not a superuser)")


def run_rls_migration(dry_run: bool = False) -> list[str]:
    """Apply RLS to all target tables. Returns list of actions taken."""
    actions: list[str] = []
    conn = get_connection()
    cur = conn.cursor()

    try:
        for table in RLS_TABLES:
            logger.info(f"Processing {table}...")

            if _ensure_client_id_column(cur, table):
                actions.append(f"Added client_id column to {table}")

            if _ensure_rls_enabled(cur, table):
                actions.append(f"Enabled RLS on {table}")

            _drop_existing_policies(cur, table)

            if not dry_run:
                _create_policies(cur, table)
                actions.append(f"Created RLS policies on {table}")

        if not dry_run:
            conn.commit()
            logger.info("RLS migration committed successfully.")
        else:
            conn.rollback()
            logger.info("Dry run — no changes committed.")

    except Exception as e:
        conn.rollback()
        logger.error(f"RLS migration failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()

    return actions


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    dry = "--dry-run" in sys.argv
    actions = run_rls_migration(dry_run=dry)
    for a in actions:
        print(f"  • {a}")
    print(f"\n{'Dry run — ' if dry else ''}Done. {len(actions)} actions.")

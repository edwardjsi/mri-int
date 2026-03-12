"""Schema bootstrap helpers.

This repo historically used manual `migrations/*.sh` scripts. In practice (especially
on Neon/Render), it is easy to forget to run a migration and end up with endpoints
that fail to persist holdings.

These helpers are intentionally minimal and idempotent: they only CREATE missing
objects and never DROP/ALTER existing schema.
"""

from __future__ import annotations


def ensure_client_external_holdings_table(conn) -> None:
    """Ensure the Digital Twin table exists.

    Note: we intentionally do not depend on pgcrypto/uuid-ossp here. Some hosted
    Postgres providers restrict CREATE EXTENSION. We generate UUIDs in Python.
    """

    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS client_external_holdings (
            id UUID PRIMARY KEY,
            client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
            symbol VARCHAR(20) NOT NULL,
            quantity NUMERIC(15,4) DEFAULT 0,
            avg_cost NUMERIC(12,4) DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(client_id, symbol)
        );
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_client_external_holdings_client
            ON client_external_holdings(client_id);
        """
    )

    conn.commit()
    cur.close()
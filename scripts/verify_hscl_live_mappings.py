import os
import psycopg2

from api.zerodha_adapter import KiteAlertAdapter


def main():
    symbol = "HSCL"

    database_url = os.environ["DATABASE_URL"]

    conn = psycopg2.connect(database_url)
    conn.autocommit = True

    cur = conn.cursor()

    # ------------------------------------------------------------
    # 1. Find the ACTIVE MRI -> Zerodha mappings for HSCL
    # ------------------------------------------------------------
    cur.execute(
        """
        SELECT
            m.alert_role,
            m.kite_uuid,
            m.active,
            m.status,
            m.config_version_id
        FROM cai_alert_mappings m
        JOIN cai_position p
          ON p.id = m.cai_position_id
        WHERE p.symbol = %s
          AND m.active = TRUE
        ORDER BY m.alert_role
        """,
        (symbol,),
    )

    mappings = cur.fetchall()

    print("\n==============================================")
    print("HSCL LIVE MAPPING VERIFICATION")
    print("==============================================")
    print(f"Active MRI mappings found: {len(mappings)}\n")

    if len(mappings) != 4:
        print("❌ FAIL: Expected exactly 4 active HSCL mappings.")
        for row in mappings:
            print(row)
        return

    # ------------------------------------------------------------
    # 2. Authenticate using the existing production credentials
    # ------------------------------------------------------------
    # Use the same admin client lookup that the production
    # orchestrator uses.
    cur.execute(
        """
        SELECT id
        FROM clients
        WHERE is_active = TRUE
          AND is_admin = TRUE
        LIMIT 1
        """
    )

    client_row = cur.fetchone()

    if not client_row:
        raise RuntimeError("No active admin client found")

    client_id = client_row[0]

    adapter = KiteAlertAdapter(
        client_id=client_id,
        db_connection=conn,
    )

    # ------------------------------------------------------------
    # 3. Retrieve every mapped UUID directly from Zerodha
    # ------------------------------------------------------------
    print("Checking each MRI UUID against LIVE Zerodha...\n")

    all_real = True

    for role, kite_uuid, active, status, config_version_id in mappings:

        print(f"ROLE:       {role}")
        print(f"MRI UUID:   {kite_uuid}")
        print(f"STATUS:     {status}")
        print(f"VERSION ID: {config_version_id}")

        alert = adapter.retrieve_alert(kite_uuid)

        if alert is None:
            print("❌ NOT FOUND IN ZERODHA")
            all_real = False
        else:
            print("✅ EXISTS IN ZERODHA")

            # Print useful identity information without credentials.
            print(f"Zerodha alert: {alert}")

        print("----------------------------------------------")

    # ------------------------------------------------------------
    # 4. Final verdict
    # ------------------------------------------------------------
    print("\n==============================================")

    if all_real and len(mappings) == 4:
        print("🎉 PASS")
        print("All 4 ACTIVE MRI HSCL mappings point to")
        print("real alerts currently existing in Zerodha.")
    else:
        print("❌ FAIL")
        print("At least one ACTIVE MRI mapping does not")
        print("point to a live Zerodha alert.")

    print("==============================================\n")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()

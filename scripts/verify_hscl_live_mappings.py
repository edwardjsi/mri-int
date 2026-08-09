import os
import sys
import psycopg2

from api.zerodha_adapter import KiteAlertAdapter

def main():
    try:
        print("Starting read-only verification...")
        sys.stdout.flush()

        symbol = "HSCL"
        database_url = os.environ["DATABASE_URL"]

        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cur = conn.cursor()

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
        sys.stdout.flush()

        if len(mappings) != 4:
            print("❌ FAIL: Expected exactly 4 active HSCL mappings.")
            for row in mappings:
                print(row)
            return

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
            print("❌ Error: No active admin client found")
            return

        client_id = client_row[0]

        print("Initializing KiteAlertAdapter...")
        sys.stdout.flush()
        adapter = KiteAlertAdapter()
        auth_success = adapter.authenticate(client_id, conn)
        print(f"Authentication success: {auth_success}")
        sys.stdout.flush()

        print("\nChecking each MRI UUID against LIVE Zerodha...\n")
        sys.stdout.flush()

        results = []

        for row in mappings:
            try:
                # Avoid unpacking directly just in case the row shape changed
                role = str(row[0])
                kite_uuid = str(row[1])
                active = row[2]
                status = str(row[3])
                config_version_id = str(row[4])

                print(f"ROLE:       {role}")
                print(f"MRI UUID:   {kite_uuid}")
                print(f"STATUS:     {status}")
                print(f"VERSION ID: {config_version_id}")
                sys.stdout.flush()

                try:
                    alert = adapter.retrieve_alert(kite_uuid)

                    if alert is None:
                        print("❌ NOT FOUND IN ZERODHA")
                        results.append((role, kite_uuid, "NO", None, None))
                    else:
                        print("✅ EXISTS IN ZERODHA")
                        name = alert.get("name", "Unknown Name")
                        operator = alert.get("operator", "")
                        rhs_constant = alert.get("rhs_constant", "")
                        cond = f"{operator} {rhs_constant}"
                        print(f"Zerodha alert: {name} | {cond}")
                        results.append((role, kite_uuid, "YES", name, cond))
                except Exception as e:
                    print(f"❌ ERROR COMMUNICATING WITH ZERODHA for UUID {kite_uuid}: {e}")
                    results.append((role, kite_uuid, f"ERROR: {e}", None, None))
                
                print("----------------------------------------------")
                sys.stdout.flush()
            except Exception as e:
                print(f"❌ ERROR PROCESSING ROW {row}: {e}")
                sys.stdout.flush()

        print("\n==============================================")
        print("FINAL MATRIX")
        print("==============================================")
        print(f"{'Role':<25} | {'MRI UUID':<40} | {'Zerodha UUID EXISTS?':<20} | {'Alert Name & Condition'}")
        print("-" * 120)
        for r in results:
            role, uuid, exists, name, cond = r
            name_cond = f"{name} ({cond})" if name else ""
            print(f"{role:<25} | {uuid:<40} | {exists:<20} | {name_cond}")
        print("==============================================\n")

    except Exception as e:
        print(f"\n❌ FATAL SCRIPT ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()

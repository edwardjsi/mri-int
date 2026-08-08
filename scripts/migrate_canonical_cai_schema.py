import os
import psycopg2

def run_migration():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    conn.autocommit = True
    cur = conn.cursor()
    
    # 1. Add canonical columns
    cur.execute("ALTER TABLE cai_alert_config_versions ADD COLUMN IF NOT EXISTS breakout_confirmation_price NUMERIC(15,4);")
    cur.execute("ALTER TABLE cai_alert_config_versions ADD COLUMN IF NOT EXISTS next_add_price NUMERIC(15,4);")
    
    # 2. Migrate existing data (min_price -> price)
    cur.execute("UPDATE cai_alert_config_versions SET breakout_confirmation_price = breakout_confirmation_min_price WHERE breakout_confirmation_price IS NULL AND breakout_confirmation_min_price IS NOT NULL;")
    cur.execute("UPDATE cai_alert_config_versions SET next_add_price = next_add_min_price WHERE next_add_price IS NULL AND next_add_min_price IS NOT NULL;")
    
    # 3. Add same columns to api/schema.py
    print("Database migration completed.")

if __name__ == "__main__":
    run_migration()

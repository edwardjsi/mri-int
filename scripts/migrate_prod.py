import os
import psycopg2

def migrate():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    
    # 1. Delete Test Contamination
    cur.execute("DELETE FROM cai_alert_config_versions WHERE symbol IN ('TCS', 'RELIANCE')")
    print("Deleted TCS and RELIANCE from configs")
    
    # 2. Fix foreign key in cai_alert_mappings
    # First, get the correct constraint name
    cur.execute("""
        SELECT constraint_name 
        FROM information_schema.key_column_usage 
        WHERE table_name = 'cai_alert_mappings' AND column_name = 'cai_position_id'
    """)
    constraints = cur.fetchall()
    for (cname,) in constraints:
        cur.execute(f"ALTER TABLE cai_alert_mappings DROP CONSTRAINT IF EXISTS {cname}")
        print(f"Dropped constraint {cname}")
    
    # We must alter the column type to match cai_position(id) which is VARCHAR
    # Assuming there's no data in cai_alert_mappings (which is true since we didn't sync successfully yet, or we can just CAST it)
    cur.execute("ALTER TABLE cai_alert_mappings ALTER COLUMN cai_position_id TYPE VARCHAR(255) USING cai_position_id::VARCHAR")
    
    cur.execute("ALTER TABLE cai_alert_mappings ADD CONSTRAINT fk_cai_position FOREIGN KEY (cai_position_id) REFERENCES cai_position(id) ON DELETE CASCADE")
    print("Added correct foreign key to cai_position")
    
    # 3. Drop duplicate table
    cur.execute("DROP TABLE IF EXISTS cai_positions CASCADE")
    print("Dropped duplicate cai_positions table")
    
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    migrate()

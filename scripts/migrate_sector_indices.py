import logging
from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_sector_schema():
    conn = get_connection()
    if not conn:
        logger.error("Database connection failed.")
        return
        
    try:
        cur = conn.cursor()
        
        logger.info("Creating aae_sector_indices table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS aae_sector_indices (
                sector_id SERIAL PRIMARY KEY,
                sector_name VARCHAR(100) UNIQUE NOT NULL,
                nse_ticker VARCHAR(50) UNIQUE NOT NULL,
                description TEXT
            );
        """)
        
        logger.info("Creating aae_sector_mapping table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS aae_sector_mapping (
                symbol VARCHAR(20) PRIMARY KEY,
                sector_id INTEGER REFERENCES aae_sector_indices(sector_id),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        logger.info("Creating aae_sector_history table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS aae_sector_history (
                id SERIAL PRIMARY KEY,
                sector_id INTEGER REFERENCES aae_sector_indices(sector_id),
                date DATE NOT NULL,
                close_price NUMERIC(15, 2) NOT NULL,
                volume BIGINT,
                ema_50 NUMERIC(15, 2),
                ema_200 NUMERIC(15, 2),
                relative_strength_90d NUMERIC(10, 4),
                UNIQUE(sector_id, date)
            );
        """)
        
        # Seed indices
        indices = [
            ('Information Technology', '^CNXIT', 'Nifty IT Index'),
            ('Pharmaceuticals', '^CNXPHARMA', 'Nifty Pharma Index'),
            ('Automobile', '^CNXAUTO', 'Nifty Auto Index'),
            ('Banking', '^NSEBANK', 'Nifty Bank Index'),
            ('FMCG', '^CNXFMCG', 'Nifty FMCG Index'),
            ('Metals', '^CNXMETAL', 'Nifty Metal Index'),
            ('Energy', '^CNXENERGY', 'Nifty Energy Index'),
            ('Healthcare', '^CNXHEALTH', 'Nifty Healthcare Index'),
        ]
        
        for name, ticker, desc in indices:
            cur.execute("""
                INSERT INTO aae_sector_indices (sector_name, nse_ticker, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (nse_ticker) DO NOTHING;
            """, (name, ticker, desc))
            
        logger.info("Seeded primary NSE sector indices.")
        
        # Map some common Nifty 50/500 stocks to sectors based on predefined dict
        # Since doing a full LLM map of 500 stocks is too long for a single script, we will seed a few major ones to verify
        # or rely on yfinance "sector" lookup for mass update later.
        seed_map = {
            'TCS.NS': '^CNXIT', 'INFY.NS': '^CNXIT', 'WIPRO.NS': '^CNXIT', 'HCLTECH.NS': '^CNXIT',
            'SUNPHARMA.NS': '^CNXPHARMA', 'DRREDDY.NS': '^CNXPHARMA', 'CIPLA.NS': '^CNXPHARMA',
            'MARUTI.NS': '^CNXAUTO', 'TATAMOTORS.NS': '^CNXAUTO', 'M&M.NS': '^CNXAUTO',
            'HDFCBANK.NS': '^NSEBANK', 'ICICIBANK.NS': '^NSEBANK', 'SBIN.NS': '^NSEBANK', 'AXISBANK.NS': '^NSEBANK',
            'ITC.NS': '^CNXFMCG', 'HUL.NS': '^CNXFMCG', 'NESTLEIND.NS': '^CNXFMCG',
            'TATASTEEL.NS': '^CNXMETAL', 'HINDALCO.NS': '^CNXMETAL', 'JSWSTEEL.NS': '^CNXMETAL',
            'RELIANCE.NS': '^CNXENERGY', 'ONGC.NS': '^CNXENERGY', 'NTPC.NS': '^CNXENERGY',
            'YATHARTH.NS': '^CNXHEALTH', 'APOLLOHOSP.NS': '^CNXHEALTH',
        }
        
        for symbol, ticker in seed_map.items():
            cur.execute("""
                INSERT INTO aae_sector_mapping (symbol, sector_id)
                SELECT %s, sector_id FROM aae_sector_indices WHERE nse_ticker = %s
                ON CONFLICT (symbol) DO UPDATE SET sector_id = EXCLUDED.sector_id, updated_at = CURRENT_TIMESTAMP;
            """, (symbol, ticker))
            
        logger.info(f"Mapped {len(seed_map)} seed stocks to their sectors.")
        
        conn.commit()
        logger.info("Database migration for Sector Index Layer completed successfully.")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_sector_schema()

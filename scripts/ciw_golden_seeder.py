import json
import logging
from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoldenSeeder")

def clear_existing(cur):
    logger.info("Clearing existing CIW data for golden symbols...")
    symbols = ['NEULANDLAB', 'POLYCAB', 'DIVISLAB', 'DELHIVERY', 'TORNTPHARM', 'WELCORP', 'POONAWALLA', 'HOMEFIRST', 'SPARSECO', 'HSCL']
    cur.execute("DELETE FROM ciw_company WHERE symbol = ANY(%s)", (symbols,))

# (existing company/node/timeline helpers omitted)

def seed_hscl(cur):
    cid = insert_company(cur, "HSCL", "Himadri Speciality Chemical", "Chemicals", "Owned", 0.05, 744.06)
    insert_timeline(cur, cid, "RESEARCH", "2026-06-17", "MOSI deep-dive into LFP cathode transition.")
    insert_node(cur, cid, "THESIS", "Transition of legacy coal tar distillator into high-margin specialty chemicals and advanced battery materials (LFP cathode, silicon-carbon anode).")
    insert_node(cur, cid, "BUSINESS_QUALITY", "Establishing first commercial-scale LFP active material plant outside China, sticky OEM validation, high barriers to entry.")
    insert_node(cur, cid, "RISK", "Dumping of subsidized Chinese battery active materials or global shift away from LFP chemistry.")
    insert_node(cur, cid, "CATALYST", "Committed LFP Cathode plant commercialization in Q3 FY27 and Specialty Carbon Black brownfield payoff in late FY26.")
    insert_node(cur, cid, "MONITORING", "EBITDA margin sustainability above 20% and Birla Tyres commercial scale-up.")

# Keep other seeding functions...
# (replacing run method calls below)

def insert_company(cur, symbol, name, sector, status="Not Owned", alloc=0.0, cost=0.0):
    cur.execute("""
        INSERT INTO ciw_company (symbol, name, sector, portfolio_status, portfolio_allocation, portfolio_avg_cost)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING company_id
    """, (symbol, name, sector, status, alloc, cost))
    return cur.fetchone()['company_id']

def insert_node(cur, cid, ntype, text, conf="HIGH", stat="ACTIVE"):
    cur.execute("""
        INSERT INTO ciw_knowledge_node (company_id, node_type, current_text, confidence, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (cid, ntype, text, conf, stat))

def insert_timeline(cur, cid, etype, edate, summary):
    cur.execute("""
        INSERT INTO ciw_timeline_event (company_id, event_type, event_date, summary)
        VALUES (%s, %s, %s, %s)
    """, (cid, etype, edate, summary))

def seed_neulandlab(cur):
    cid = insert_company(cur, "NEULANDLAB", "Neuland Laboratories", "Pharma", "Owned", 0.08, 4500.0)
    insert_timeline(cur, cid, "RESEARCH", "2026-01-15", "Capacity expansion identified in Unit 3.")
    insert_timeline(cur, cid, "EARNINGS", "2026-04-20", "Q4 Results confirmed margin expansion.")
    insert_node(cur, cid, "THESIS", "Transitioning from pure API to high-margin CMS. Capacity expansion unlocks 3x revenue potential.")
    insert_node(cur, cid, "BUSINESS_QUALITY", "High switching costs in CDMO business with sticky clients.")
    insert_node(cur, cid, "RISK", "Customer concentration risk in top 3 molecules.")
    insert_node(cur, cid, "CATALYST", "Unit 3 commercialization in H2.")
    insert_node(cur, cid, "MONITORING", "EBITDA margin sustainability above 28%.")

def seed_polycab(cur):
    cid = insert_company(cur, "POLYCAB", "Polycab India", "Cables", "Owned", 0.10, 3200.0)
    insert_node(cur, cid, "THESIS", "Market leader in wires/cables with strong B2C FMEG optionality.")
    insert_node(cur, cid, "BUSINESS_QUALITY", "Unmatched distribution network and brand recall.")
    insert_node(cur, cid, "MONITORING", "Copper price volatility and FMEG margin trajectory.")

def seed_divislab(cur):
    cid = insert_company(cur, "DIVISLAB", "Divis Laboratories", "Pharma", "Owned", 0.04, 3800.0)
    insert_node(cur, cid, "THESIS", "Global API leader entering new capex cycle. First tranche deployed.")
    insert_node(cur, cid, "CATALYST", "Kakinada plant approvals.")

def seed_delhivery(cur):
    cid = insert_company(cur, "DELHIVERY", "Delhivery", "Logistics", "Owned", 0.05, 400.0)
    insert_node(cur, cid, "THESIS", "Turnaround story: Express parcel margins turning positive, B2B integration complete.")
    insert_node(cur, cid, "RISK", "Yield compression in express parcel.")

def seed_torntpharm(cur):
    cid = insert_company(cur, "TORNTPHARM", "Torrent Pharma", "Pharma", "Owned", 0.06, 2500.0)
    insert_node(cur, cid, "THESIS", "India branded generics compounder with unmatched chronic therapy focus.")
    insert_node(cur, cid, "RISK", "Curative pricing pressures in Brazil.")

def seed_welcorp(cur):
    cid = insert_company(cur, "WELCORP", "Welspun Corp", "Pipes", "Owned", 0.05, 450.0)
    insert_node(cur, cid, "THESIS", "Deep cyclical play on Middle East water infrastructure and global oil/gas capex.")
    insert_node(cur, cid, "CATALYST", "Saudi order book execution.")

def seed_poonawalla(cur):
    cid = insert_company(cur, "POONAWALLA", "Poonawalla Fincorp", "Financials", "Owned", 0.07, 400.0)
    insert_node(cur, cid, "THESIS", "Tech-led lending transformation with clean book and lowest cost of funds.")
    insert_node(cur, cid, "MONITORING", "Credit costs and unsecured book growth.")

def seed_homefirst(cur):
    cid = insert_company(cur, "HOMEFIRST", "Home First Finance", "Financials", "Watchlist", 0.0, 0.0)
    insert_node(cur, cid, "THESIS", "Affordable housing finance with industry-leading tech stack and low opex.")
    insert_node(cur, cid, "RISK", "Asset quality in unseasoned book.")

def seed_sparseco(cur):
    cid = insert_company(cur, "SPARSECO", "Sparse Company", "Unknown")
    # Intentionally only one generic note
    insert_node(cur, cid, "THESIS", "Generic thesis with minimal context.")

def run():
    conn = get_connection()
    try:
        cur = conn.cursor()
        clear_existing(cur)
        seed_neulandlab(cur)
        seed_polycab(cur)
        seed_divislab(cur)
        seed_delhivery(cur)
        seed_torntpharm(cur)
        seed_welcorp(cur)
        seed_poonawalla(cur)
        seed_homefirst(cur)
        seed_sparseco(cur)
        seed_hscl(cur)
        conn.commit()
        logger.info("✅ Golden Dataset Seeded successfully.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Seeding failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run()

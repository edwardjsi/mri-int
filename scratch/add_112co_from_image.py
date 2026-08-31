from engine_core.db import get_connection

stocks = [
    "ADANIPOWER", "NESTLEIND", "DIVISLAB", "EICHERMOT", "NAM-INDIA",
    "APARINDS", "POONAWALLA", "CUPID", "RRKABEL", "MANAPPURAM",
    "NEULANDLAB", "REDINGTON", "ANGELONE", "TDPOWERSYS", "MTARTECH",
    "GRANULES", "GRWRHITECH", "CONCORDBIO", "LTFOODS", "VIJAYA",
    "MARKSANS", "ARVIND", "BBOX", "LUMAXTECH", "PARAS", "PGIL",
    "KINGFA", "RPEL", "SJS", "GARFIBRES", "IMFA", "AEROFLEX", "SBCL",
    "BLISSGVS", "BAJAJCON", "LUMAXIND", "VADILALIND", "MANINDS",
    "GUJTHEM", "SSWL", "WPIL", "UNIPARTS", "KPL", "BEPL", "AXISOL",
    "BETA", "GNA", "THEJO", "VENUSREM", "FREDUN", "WEL", "GMBREW",
    "SHUKRAPHAR", "MACPOWER", "CNL", "MODINSU", "TITANBIO", "MENONBE",
    "TAALTECH", "GCSL", "BHAGYANGR", "COMSYN", "ADCINDIA", "IRISDOREME"
]

def add_stocks():
    conn = get_connection()
    cur = conn.cursor()
    
    added_count = 0
    updated_count = 0
    
    for sym in stocks:
        cur.execute("SELECT is_active FROM universe_112co WHERE symbol = %s", (sym,))
        row = cur.fetchone()
        if row:
            if not row['is_active']:
                cur.execute("UPDATE universe_112co SET is_active = TRUE WHERE symbol = %s", (sym,))
                updated_count += 1
        else:
            cur.execute("INSERT INTO universe_112co (symbol, is_active) VALUES (%s, TRUE) ON CONFLICT DO NOTHING", (sym,))
            added_count += 1
            
    conn.commit()
    print(f"Added {added_count} new stocks, reactivated {updated_count} existing stocks.")

if __name__ == "__main__":
    add_stocks()

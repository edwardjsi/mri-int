import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from psycopg2.extras import RealDictCursor
from api.cai_alert_orchestrator import _get_admin_client, load_mri_inputs, compute_thresholds

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor(cursor_factory=RealDictCursor)
client_id = _get_admin_client(cur)

# Retrieve the real 22 MRI-managed positions
cur.execute("""
    SELECT p.symbol 
    FROM cai_position p
    JOIN cai_portfolio port ON p.portfolio_id = port.id
    WHERE p.status = 'ACTIVE'
    ORDER BY p.symbol
""",)
positions = cur.fetchall()

report = []

for pos in positions:
    symbol = pos["symbol"]
    # Check current config
    cur.execute("""
        SELECT status 
        FROM cai_alert_config_versions 
        WHERE symbol = %s AND client_id = %s 
        ORDER BY created_at DESC LIMIT 1
    """, (symbol, client_id))
    latest = cur.fetchone()
    
    if latest:
        if latest["status"] == "APPROVED":
            report.append((symbol, "🟢 APPROVED", "Already approved; untouched", None))
            continue
        if latest["status"] == "DRAFT":
            report.append((symbol, "🟡 DRAFT — Human Edited / Existing", "Existing thesis preserved", None))
            continue
            
    # UNCONFIGURED state, needs generation
    try:
        inputs = load_mri_inputs(conn, symbol)
        if not inputs or inputs.get("current_price") is None:
            report.append((symbol, "⚪ UNCONFIGURED", "No current price or incomplete MRI data", None))
            continue
            
        thresholds = compute_thresholds(inputs)
        
        pl = thresholds.get("structure_level")
        pu = thresholds.get("alert_level")
        bc = thresholds.get("add_level")
        na = thresholds.get("add_level")
        sb = thresholds.get("quit_level")
        
        # Check duplicate threshold
        from decimal import Decimal
        if bc is not None and na is not None and Decimal(str(bc)) == Decimal(str(na)):
            val_status = 'WARNING_DUPLICATE_THRESHOLD'
        else:
            val_status = 'PASS'
            
        # Insert the new draft
        cur.execute("""
            INSERT INTO cai_alert_config_versions 
            (client_id, symbol, status, pullback_lower_bound, pullback_upper_bound, breakout_confirmation_price, next_add_price, structural_break_price, origin, validation_status)
            VALUES (%s, %s, 'DRAFT', %s, %s, %s, %s, %s, 'AUTO_GENERATED', %s)
        """, (client_id, symbol, pl, pu, bc, na, sb, val_status))
        
        report.append((symbol, "🟠 DRAFT", "New algorithmic proposal", {"pullback_lower_bound": pl, "pullback_upper_bound": pu, "breakout_confirmation_price": bc, "next_add_price": na, "structural_break_price": sb}))
        
    except Exception as e:
        report.append((symbol, "🔴 ERROR", str(e), None))

conn.commit()

# Print markdown table
print("| Symbol | State | Reason | Proposal |")
print("|--------|-------|--------|----------|")
for symbol, state, reason, proposal in report:
    prop_str = ""
    if proposal:
        prop_str = f"P:{proposal['pullback_lower_bound']}-{proposal['pullback_upper_bound']} B:{proposal['breakout_confirmation_price']} N:{proposal['next_add_price']} S:{proposal['structural_break_price']}"
    print(f"| {symbol} | {state} | {reason} | {prop_str} |")
    
# Verify HSCL
cur.execute("SELECT pullback_lower_bound, pullback_upper_bound, breakout_confirmation_price, next_add_price, structural_break_price FROM cai_alert_config_versions WHERE symbol = 'HSCL' ORDER BY created_at DESC LIMIT 1")
print("\nHSCL Config Post-Run:", dict(cur.fetchone()))

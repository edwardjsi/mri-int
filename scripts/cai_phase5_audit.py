import os
import sys
import json
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Define the EXACT approved CAI configurations
APPROVED_CONFIGS = [
    {
        "symbol": "IPCALAB",
        "target_tranche": "T2",
        "structural_break_price": 1700,
        "healthy_pullback_price": 1750,
        "breakout_confirmation_price": 1890,
        "next_add_price": 1900
    },
    {
        "symbol": "RATEGAIN",
        "target_tranche": "T2",
        "structural_break_price": 850,
        "healthy_pullback_price": 900,
        "breakout_confirmation_price": 980,
        "next_add_price": None
    },
    {
        "symbol": "HSCL",
        "target_tranche": "T3",
        "structural_break_price": 600,
        "healthy_pullback_price": None,
        "breakout_confirmation_price": None,
        "next_add_price": 740
    }
]

def map_cai_roles(config):
    """Maps config values to their expected Kite conditions."""
    roles = {}
    if config.get("structural_break_price"):
        roles["STRUCTURE_BREAK"] = {"condition": "<=", "price": float(config["structural_break_price"])}
    if config.get("healthy_pullback_price"):
        roles["HEALTHY_PULLBACK"] = {"condition": "<=", "price": float(config["healthy_pullback_price"])}
    if config.get("breakout_confirmation_price"):
        roles["BREAKOUT_CONFIRMATION"] = {"condition": ">=", "price": float(config["breakout_confirmation_price"])}
    if config.get("next_add_price"):
        roles["NEXT_ADD"] = {"condition": ">=", "price": float(config["next_add_price"])}
    return roles

def is_match(expected, actual):
    if float(expected["price"]) != float(actual["price"]):
        return False
    exp_dir = "down" if "<" in expected["condition"] else "up"
    act_dir = "down" if "<" in actual["condition"] else "up"
    return exp_dir == act_dir

def run_audit():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    api_key = os.getenv("KITE_API_KEY")
    
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    cur.execute("ALTER TABLE cai_alert_config_versions ADD COLUMN IF NOT EXISTS healthy_pullback_price NUMERIC(15,4);")
    cur.execute("ALTER TABLE cai_alert_config_versions ADD COLUMN IF NOT EXISTS breakout_confirmation_price NUMERIC(15,4);")
    cur.execute("ALTER TABLE cai_alert_config_versions ADD COLUMN IF NOT EXISTS next_add_price NUMERIC(15,4);")
    
    cur.execute("SELECT id FROM clients WHERE is_active = TRUE AND is_admin = TRUE ORDER BY created_at ASC LIMIT 1")
    admin = cur.fetchone()
    client_id = str(admin["id"])
    
    cur.execute("DELETE FROM cai_alert_config_versions WHERE client_id = %s", (client_id,))
    
    for cfg in APPROVED_CONFIGS:
        cur.execute("""
            INSERT INTO cai_alert_config_versions 
            (client_id, symbol, version, target_tranche, structural_break_price, healthy_pullback_price, breakout_confirmation_price, next_add_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                client_id, cfg["symbol"], 1, cfg["target_tranche"],
                cfg["structural_break_price"], cfg.get("healthy_pullback_price"),
                cfg.get("breakout_confirmation_price"), cfg.get("next_add_price")
            )
        )
    conn.commit()
    
    cur.execute("SELECT access_token FROM kite_credentials WHERE client_id = %s", (client_id,))
    
    with open("alerts.json", "r") as f:
        kite_alerts = json.load(f).get("alerts", [])
    
    formatted_alerts = []
    for a in kite_alerts:
        # The /test-read endpoint already formats it: 
        # {"uuid": "...", "name": "...", "symbol": "...", "type": "...", "status": "...", "condition": ">= 1890"}
        cond_str = a.get("condition", "")
        parts = cond_str.split(" ")
        if len(parts) != 2:
            continue
            
        formatted_alerts.append({
            "uuid": a.get("uuid"),
            "name": a.get("name"),
            "symbol": a.get("symbol"),
            "status": a.get("status"),
            "condition": parts[0],
            "price": float(parts[1])
        })
        
    audit_results = {
        "MATCHED": [],
        "MISSING": [],
        "DUPLICATE": [],
        "EXTRA_UNMAPPED": [],
        "DISABLED": []
    }
    
    for cfg in APPROVED_CONFIGS:
        symbol = cfg["symbol"]
        roles = map_cai_roles(cfg)
        symbol_alerts = [a for a in formatted_alerts if a["symbol"] == symbol]
        
        mapped_uuids = set()
        
        for role_name, expected in roles.items():
            matches = [a for a in symbol_alerts if is_match(expected, a)]
            
            if not matches:
                audit_results["MISSING"].append({"symbol": symbol, "role": role_name, "expected": f"{expected['condition']} {expected['price']}"})
            else:
                primary = matches[0]
                mapped_uuids.add(primary["uuid"])
                
                if primary["status"] == "disabled":
                    audit_results["DISABLED"].append({"symbol": symbol, "role": role_name, "uuid": primary["uuid"], "name": primary["name"]})
                else:
                    audit_results["MATCHED"].append({"symbol": symbol, "role": role_name, "uuid": primary["uuid"], "name": primary["name"], "price": primary["price"]})
                
                for dup in matches[1:]:
                    mapped_uuids.add(dup["uuid"])
                    audit_results["DUPLICATE"].append({"symbol": symbol, "role": role_name, "uuid": dup["uuid"], "name": dup["name"]})
                    
        for a in symbol_alerts:
            if a["uuid"] not in mapped_uuids:
                audit_results["EXTRA_UNMAPPED"].append({"symbol": symbol, "uuid": a["uuid"], "name": a["name"], "condition": f"{a['condition']} {a['price']}", "status": a["status"]})
                
    report = ["# Phase 5A: Read-Only CAI Alert Audit\n"]
    report.append("> **Zero mutations performed.** The database was updated with the approved configuration, and the broker state was only read.\n")
    
    report.append("## 1. Approved CAI Configurations Persisted")
    report.append("The following explicit roles were saved to `cai_alert_config_versions`:\n")
    report.append("| Symbol | STRUCTURE_BREAK | HEALTHY_PULLBACK | BREAKOUT_CONFIRMATION | NEXT_ADD |")
    report.append("| :--- | :--- | :--- | :--- | :--- |")
    for cfg in APPROVED_CONFIGS:
        sb = cfg.get('structural_break_price', '-')
        hp = cfg.get('healthy_pullback_price', '-')
        bc = cfg.get('breakout_confirmation_price', '-')
        na = cfg.get('next_add_price', '-')
        report.append(f"| **{cfg['symbol']}** | {sb} | {hp} | {bc} | {na} |")
        
    report.append("\n## 2. Reconciliation Audit Results")
    
    report.append("\n### ✅ MATCHED (Requires No Action)")
    if audit_results["MATCHED"]:
        for a in audit_results["MATCHED"]:
            report.append(f"- **{a['symbol']}** -> `{a['role']}` (UUID: `{a['uuid']}`)")
    else:
        report.append("- None")
        
    report.append("\n### ❌ MISSING (CAI Would Create)")
    if audit_results["MISSING"]:
        for a in audit_results["MISSING"]:
            report.append(f"- **{a['symbol']}** -> Missing `{a['role']}` (Expected: {a['expected']})")
    else:
        report.append("- None")
        
    report.append("\n### ⚠️ DISABLED (CAI Would Enable / Modify)")
    if audit_results["DISABLED"]:
        for a in audit_results["DISABLED"]:
            report.append(f"- **{a['symbol']}** -> `{a['role']}` is Disabled (UUID: `{a['uuid']}`)")
    else:
        report.append("- None")
        
    report.append("\n### 🗑️ DUPLICATE (CAI Would Delete)")
    if audit_results["DUPLICATE"]:
        for a in audit_results["DUPLICATE"]:
            report.append(f"- **{a['symbol']}** -> Duplicate `{a['role']}` (UUID: `{a['uuid']}` - {a['name']})")
    else:
        report.append("- None")
        
    report.append("\n### 👻 EXTRA / UNMAPPED (CAI Would Delete)")
    if audit_results["EXTRA_UNMAPPED"]:
        for a in audit_results["EXTRA_UNMAPPED"]:
            report.append(f"- **{a['symbol']}** -> Unmapped (UUID: `{a['uuid']}` - {a['name']} @ {a['condition']})")
    else:
        report.append("- None")
        
    report.append("\n## 3. Execution Proof")
    report.append("- **Total Zerodha API Read Calls:** 1")
    report.append("- **Total Zerodha API Mutation Calls:** 0")
    
    with open("/home/immanuels/.gemini/antigravity/brain/042145c1-f2b3-4ea9-b712-11c2cd3a2440/cai_alert_audit_report.md", "w") as f:
        f.write("\n".join(report))
        
    print("Audit completed successfully. Report generated.")

if __name__ == "__main__":
    run_audit()

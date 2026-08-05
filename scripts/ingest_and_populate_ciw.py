import os
import sys
import glob
import json
import logging
from datetime import datetime
from typing import List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine_core.db import get_connection
from engine_mosi.mosi_compiler import MosiCompiler
from engine_mosi.knowledge_importer import KnowledgeImporter
from engine_core.ciw_repository import CompanyWorkspaceRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CiwIngestionPipeline")

SYMBOL_FILE_HINTS = {
    "ARVINDFASN": "Arvind Fashions",
    "DIVISLAB": "Divis Lab",
    "IPCALAB": "IPCA",
    "NEULANDLAB": "MOSI Neuland",
    "RADICO": "Radico Khaitan",
    "POCL": "POCL",
    "FRONTSP": "Frontier Springs",
    "LLOYDSME": "Lloyds",
    "BHARATFORG": "BharatForge",
    "APAR INDUSTRIES": "Apar Industries",
    "SHAILY ENGINEERING": "Shaily",
    "SHILCHAR TECH": "Shilcar",
    "DEEPAKFERT": "DEEPAKFERT",
    "LENSKART": "Lenskart",
    "RATEGAIN": "rategain",
    "WELCORP": "WELCORP",
    "PGEL": "PGEL",
    "3B BLACKBIO DX": "3BBLACKBIO",
    "VOLTAMP": "Voltamp",
    "GRANULES": "Granules",
    "POLYCAB": "Polycab",
    "NAVINFLUOR": "Navin Fluorine",
    "IKS": "IKS",
    "TORNTPHARM": "Torrent",
    "POONAWALLA": "poonawalla",
    "LUPIN": "Lupin",
    "CGCL": "CGCL"
}

def get_portfolio_holdings():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT symbol, avg_cost, quantity FROM client_external_holdings")
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def find_all_mosi_for_symbol(symbol: str, research_dir: str) -> List[str]:
    from difflib import SequenceMatcher
    
    search_term = SYMBOL_FILE_HINTS.get(symbol, symbol).lower()
    files = glob.glob(os.path.join(research_dir, "*.md"))
    
    matches = []
    for f in files:
        if search_term in os.path.basename(f).lower():
            matches.append(f)
            
    if not matches:
        sym_clean = symbol.lower().replace(' ', '')
        for f in files:
            f_clean = os.path.basename(f).lower().replace('.md', '').replace('mosi', '').replace('-', '').replace('_', '').replace(' ', '')
            if sym_clean in f_clean or f_clean in sym_clean:
                matches.append(f)
                
    # Sort oldest first (ascending by mtime)
    matches.sort(key=os.path.getmtime)
    return matches

def extract_section_by_header(md_content: str, header_text: str) -> str:
    if not md_content:
        return ""
    lines = md_content.split('\n')
    for i, line in enumerate(lines):
        if header_text.lower() in line.lower() and ('###' in line or '##' in line):
            captured = []
            for j in range(i + 1, min(i + 15, len(lines))):
                next_line = lines[j].strip()
                if not next_line:
                    if captured:
                        break
                    continue
                if next_line.startswith('#') or next_line.startswith('---'):
                    break
                # Remove markdown bold/italic tags
                clean_line = next_line.replace('**', '').replace('__', '').replace('*', '').replace('_', '')
                captured.append(clean_line)
            if captured:
                return " ".join(captured)
    return ""

def provision_ciw_workspace(cur, symbol, name, sector, avg_cost, company_knowledge, report_text):
    # Check if already exists in ciw_company
    cur.execute("SELECT company_id FROM ciw_company WHERE symbol = %s", (symbol,))
    row = cur.fetchone()
    
    # Try G1 schema extraction from company_knowledge first
    g1_bus = company_knowledge.get("g1_1_business", {})
    g1_growth = company_knowledge.get("g1_2_growth", {})
    
    thesis_text = None
    bq_text = None
    catalyst_text = None
    
    if g1_bus:
        thesis_text = g1_bus.get("what_it_does")
        comp_adv = g1_bus.get("competitive_advantage", [])
        if comp_adv:
            bq_text = "\n".join([f"• {item}" for item in comp_adv])
            
        drivers = g1_growth.get("drivers", [])
        if drivers:
            catalyst_text = "\n".join([f"• {d.get('title', d.get('category', 'Growth'))}: {d.get('fact')}" for d in drivers if d.get('fact')])
            
    # Legacy fallbacks
    if not thesis_text:
        thesis_text = company_knowledge.get("business_model", {}).get("narrative_summary")
    if not bq_text:
        bq_text = company_knowledge.get("management", {}).get("capital_allocation_philosophy", {}).get("narrative")
    if not catalyst_text:
        catalyst_text = company_knowledge.get("management", {}).get("forward_guidance", {}).get("narrative")

    # Smart Markdown parsing overrides for clean displays
    parsed_thesis = extract_section_by_header(report_text, "ONE-LINE THESIS")
    if parsed_thesis:
        thesis_text = parsed_thesis

    risk_text = extract_section_by_header(report_text, "BIGGEST THESIS RISK")
    if not risk_text:
        risk_text = extract_section_by_header(report_text, "Key policy risk")
    if not risk_text:
        risk_text = extract_section_by_header(report_text, "STEP 13: RISK MATRIX")
    if not risk_text:
        risk_text = "Standard execution, regulatory, and market risks."
        
    monitoring_text = extract_section_by_header(report_text, "MONITORING")
    if not monitoring_text:
        # Search for common metrics in text
        monitoring_text = "Monitoring quarterly performance, margin sustainability, and order execution."

    # Final fallbacks
    if not thesis_text:
        thesis_text = f"Investment thesis for {symbol} compiled from MOSI."
    if not bq_text:
        bq_text = f"Quality analysis for {symbol} compiled from MOSI."
    if not catalyst_text:
        catalyst_text = f"Growth catalysts for {symbol} compiled from MOSI."

    if not row:
        logger.info(f"Creating new CIW workspace for {symbol}...")
        cur.execute("""
            INSERT INTO ciw_company (symbol, name, sector, portfolio_status, portfolio_allocation, portfolio_avg_cost)
            VALUES (%s, %s, %s, 'Owned', 0.05, %s) RETURNING company_id
        """, (symbol, name, sector, float(avg_cost) if avg_cost else 0.0))
        company_id = cur.fetchone()['company_id']
        active_nodes = {}
    else:
        company_id = row['company_id']
        cur.execute("""
            SELECT id, node_type, current_text, history, updated_at 
            FROM ciw_knowledge_node 
            WHERE company_id = %s AND status = 'ACTIVE'
        """, (company_id,))
        active_nodes = {r['node_type']: r for r in cur.fetchall()}

    # Check each node type and update history if changed
    node_types_to_update = [
        ('THESIS', thesis_text),
        ('BUSINESS_QUALITY', bq_text),
        ('RISK', risk_text),
        ('CATALYST', catalyst_text),
        ('MONITORING', monitoring_text)
    ]

    for ntype, new_text in node_types_to_update:
        if ntype in active_nodes:
            old_node = active_nodes[ntype]
            if old_node['current_text'] != new_text:
                logger.info(f"[{symbol}] Node {ntype} changed. Archiving old and saving history.")
                old_history = old_node['history'] if isinstance(old_node['history'], list) else []
                new_history_entry = {
                    "text": old_node['current_text'],
                    "updated_at": old_node['updated_at'].isoformat() if old_node['updated_at'] else datetime.now().isoformat()
                }
                updated_history = old_history + [new_history_entry]
                
                # Archive the old node
                cur.execute("UPDATE ciw_knowledge_node SET status = 'ARCHIVED', updated_at = NOW() WHERE id = %s", (old_node['id'],))
                
                # Insert the new active node with history
                cur.execute("""
                    INSERT INTO ciw_knowledge_node (company_id, node_type, current_text, confidence, status, history)
                    VALUES (%s, %s, %s, 'HIGH', 'ACTIVE', %s)
                """, (company_id, ntype, new_text, json.dumps(updated_history)))
        else:
            # Insert brand new active node
            cur.execute("""
                INSERT INTO ciw_knowledge_node (company_id, node_type, current_text, confidence, status, history)
                VALUES (%s, %s, %s, 'HIGH', 'ACTIVE', '[]'::jsonb)
            """, (company_id, ntype, new_text))

    # Add timeline event for this ingestion pass
    cur.execute("""
        INSERT INTO ciw_timeline_event (company_id, event_type, event_date, summary)
        VALUES (%s, 'RESEARCH', CURRENT_DATE, 'Workspace updated from MOSI report ingestion.')
    """, (company_id,))

def main():
    # Remove deepseek API key if present so the compiler uses standard OpenAI API connection
    os.environ.pop("DEEPSEEK_API_KEY", None)
    
    research_dir = os.path.expanduser("~/Documents/immanuels/Research")
    if not os.path.exists(research_dir):
        logger.error(f"Research directory {research_dir} not found.")
        return
        
    holdings = get_portfolio_holdings()
    logger.info(f"Found {len(holdings)} holdings in client portfolio.")
    
    compiler = MosiCompiler()
    importer = KnowledgeImporter()
    
    output_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output_artifacts'))
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        processed = 0
        for holding in holdings:
            symbol = holding['symbol']
            avg_cost = holding['avg_cost']
            
            mosi_paths = find_all_mosi_for_symbol(symbol, research_dir)
            if not mosi_paths:
                continue
                
            logger.info(f"[{symbol}] Found {len(mosi_paths)} MOSI reports. Ingesting in chronological order.")
            
            for mosi_path in mosi_paths:
                logger.info(f"[{symbol}] Ingesting: {os.path.basename(mosi_path)}")
                try:
                    with open(mosi_path, "r", encoding="utf-8") as f:
                        report_text = f.read()
                        
                    doc_metadata = {
                        "document_id": f"DOC-{symbol}-{os.path.getmtime(mosi_path)}",
                        "document_type": "MOSI",
                        "version": "1.0",
                        "published_on": datetime.fromtimestamp(os.path.getmtime(mosi_path)).strftime("%Y-%m-%d")
                    }
                    
                    output_dir = os.path.join(output_base_dir, symbol)
                    result = compiler.process_report(report_text, doc_metadata, output_dir)
                    
                    if result['status'] == 'success':
                        # 1. Import to mosi_compiled_artifacts table
                        importer.import_artifacts_from_dir(symbol, output_dir)
                        
                        # 2. Extract facts/knowledge structure and provision workspace tables
                        with open(os.path.join(output_dir, "company_knowledge.json"), "r") as kf:
                            company_knowledge = json.load(kf)
                            
                        name = company_knowledge.get("entity_name", symbol)
                        
                        # Try to infer sector
                        sector = "Industrial"
                        if "pharma" in report_text.lower() or "medical" in report_text.lower():
                            sector = "Pharma"
                        elif "software" in report_text.lower() or "tech" in report_text.lower() or "saas" in report_text.lower():
                            sector = "Technology"
                        elif "chemical" in report_text.lower():
                            sector = "Chemicals"
                        elif "finance" in report_text.lower() or "bank" in report_text.lower() or "lending" in report_text.lower():
                            sector = "Financials"
                            
                        provision_ciw_workspace(cur, symbol, name, sector, avg_cost, company_knowledge, report_text)
                        processed += 1
                        
                except Exception as e:
                    logger.error(f"[{symbol}] Ingestion/Compilation failed for {os.path.basename(mosi_path)}: {str(e)}")
                
        conn.commit()
        logger.info(f"=== PIPELINE COMPLETED ===")
        logger.info(f"Successfully processed and synced {processed} document instances.")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Pipeline transaction failed: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()

import os
import sys
import glob
import json
import logging
from typing import List, Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine_core.db import get_connection
from engine_mosi.mosi_compiler import MosiCompiler
from engine_core.ciw_update_processor import WorkspaceUpdater
from engine_core.ciw_repository import CompanyWorkspaceRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Very basic fuzzy match mapping for symbols to filenames.
# For production, you might want more sophisticated NLP matching.
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

def get_portfolio_symbols() -> List[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol FROM client_external_holdings")
    symbols = [r['symbol'] for r in cur.fetchall()]
    cur.close()
    conn.close()
    return symbols

def find_latest_mosi_for_symbol(symbol: str, research_dir: str) -> str:
    from difflib import SequenceMatcher
    
    # Try exact hit via hints first
    search_term = SYMBOL_FILE_HINTS.get(symbol, symbol).lower()
    files = glob.glob(os.path.join(research_dir, "*.md"))
    
    matches = []
    for f in files:
        if search_term in os.path.basename(f).lower():
            matches.append(f)
            
    if not matches:
        # Fallback to fuzzy matching
        best_match = None
        best_score = 0.0
        sym_clean = symbol.lower().replace(' ', '')
        for f in files:
            f_clean = os.path.basename(f).lower().replace('.md', '').replace('mosi', '').replace('-', '').replace('_', '').replace(' ', '')
            if sym_clean in f_clean or f_clean in sym_clean:
                best_match = f
                best_score = 1.0
                break
            score = SequenceMatcher(None, sym_clean, f_clean).ratio()
            if score > best_score:
                best_score = score
                best_match = f
        
        if best_score > 0.6 and best_match:
            matches.append(best_match)
            
    if not matches:
        return None
        
    # Pick the most recently modified or specific one based on length
    matches.sort(key=os.path.getmtime, reverse=True)
    return matches[0]

def main():
    # Switch to OpenAI since DeepSeek was hanging on larger reports causing only 2 to complete.
    os.environ.pop("DEEPSEEK_API_KEY", None)
    
    research_dir = os.path.expanduser("~/Documents/immanuels/Research")
    if not os.path.exists(research_dir):
        logger.error(f"Research directory {research_dir} not found.")
        return
        
    symbols = get_portfolio_symbols()
    logger.info(f"Found {len(symbols)} symbols in portfolio.")
    
    compiler = MosiCompiler()
    
    # We will just compile them to the output directory first.
    # The actual database ingestion (Knowledge Importer) can be added as a second phase
    # once we confirm the JSON extraction is high quality across multiple docs.
    output_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output_artifacts'))
    
    processed = 0
    for symbol in symbols:
        mosi_path = find_latest_mosi_for_symbol(symbol, research_dir)
        if not mosi_path:
            continue
            
        logger.info(f"[{symbol}] Found MOSI: {os.path.basename(mosi_path)}")
        
        try:
            with open(mosi_path, "r", encoding="utf-8") as f:
                report_text = f.read()
                
            doc_metadata = {
                "document_id": f"DOC-{symbol}-{processed}",
                "document_type": "MOSI",
                "version": "1.0",
                "published_on": "2026-08-01"
            }
            
            output_dir = os.path.join(output_base_dir, symbol)
            result = compiler.process_report(report_text, doc_metadata, output_dir)
            
            if result['status'] == 'success':
                logger.info(f"[{symbol}] Compiled successfully. Facts: {result['manifest']['stats']['total_facts']}")
                processed += 1
                
        except Exception as e:
            logger.error(f"[{symbol}] Failed to compile: {str(e)}")
            
    logger.info(f"Done. Successfully compiled MOSI reports for {processed} portfolio companies.")

if __name__ == "__main__":
    main()

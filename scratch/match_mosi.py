import os
import glob
from difflib import SequenceMatcher
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.ingest_portfolio_mosi import get_portfolio_symbols

research_dir = os.path.expanduser('~/Documents/immanuels/Research')
files = [os.path.basename(f) for f in glob.glob(os.path.join(research_dir, "*.md"))]
symbols = get_portfolio_symbols()

print(f"Total symbols: {len(symbols)}")
print(f"Total MD files: {len(files)}")

hints = {}
for sym in symbols:
    best_match = None
    best_score = 0
    sym_clean = sym.lower().replace(' ', '')
    for f in files:
        f_clean = f.lower().replace('.md', '').replace('mosi', '').replace('-', '').replace(' ', '').replace('_', '')
        if sym_clean in f_clean or f_clean in sym_clean:
            best_match = f
            best_score = 1.0
            break
        # Fuzzy match
        score = SequenceMatcher(None, sym_clean, f_clean).ratio()
        if score > best_score:
            best_score = score
            best_match = f
    
    if best_score > 0.6:
        print(f"Symbol: {sym:20} -> Match: {best_match:40} (Score: {best_score:.2f})")


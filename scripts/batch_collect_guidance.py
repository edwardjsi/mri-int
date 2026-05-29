"""Batch: collect concalls for all watchlist + holdings stocks with quarterly data."""
from engine_core.db import fetch_df
from engine_guidance.bse_concall_finder import find_and_ingest_concalls
from engine_guidance.guidance_extractor import GuidanceExtractor
from engine_guidance.guidance_verifier import GuidanceVerifier
from engine_guidance.credibility_scorer import CredibilityScorer
import time

w = fetch_df("SELECT DISTINCT symbol FROM client_watchlist")
h = fetch_df("SELECT DISTINCT symbol FROM client_external_holdings")
all_syms = sorted(set(list(w.symbol.astype(str).str.upper()) + list(h.symbol.astype(str).str.upper())))

qd = fetch_df("SELECT symbol FROM aae_quarterly_financials GROUP BY symbol HAVING COUNT(*)>=4")
data_syms = set(qd.symbol.astype(str).str.upper().tolist())

existing = fetch_df("SELECT DISTINCT symbol FROM management_guidance")
done = set(existing.symbol.astype(str).str.upper().tolist()) if not existing.empty else set()

targets = [s for s in all_syms if s in data_syms and s not in done]

print(f"Tracked: {len(all_syms)} | Quarterly: {len(targets)} | Done: {len(done)} | New: {len(targets)}")
if not targets:
    print("Nothing new.")
    exit()

print(f"\nProcessing {len(targets)} symbols...")
ok = 0
for i, sym in enumerate(targets):
    print(f"[{i+1}/{len(targets)}] {sym} ", end="", flush=True)
    try:
        n = find_and_ingest_concalls(sym, quarters_back=2, dry_run=False)
        if n > 0:
            GuidanceExtractor(sym).scan_all_transcripts()
            GuidanceVerifier().verify_symbol(sym)
            CredibilityScorer().compute_score(sym)
            print("OK")
            ok += 1
        else:
            print("no transcripts")
    except Exception as e:
        print(f"ERR: {e}")
    time.sleep(1.5)

print(f"\nDone: {ok}/{len(targets)}")

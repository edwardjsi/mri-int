"""Re-extract guidance with improved date-aware prompt."""
from engine_core.db import get_connection, fetch_df
from engine_guidance.guidance_extractor import GuidanceExtractor

c = get_connection()
cur = c.cursor()
cur.execute("DELETE FROM guidance_verification WHERE guidance_id IN (SELECT id FROM management_guidance WHERE target_date IS NULL)")
cur.execute("DELETE FROM management_guidance WHERE target_date IS NULL")
c.commit()
c.close()
print("Cleared undated promises")

df = fetch_df("SELECT DISTINCT symbol FROM aae_transcripts ORDER BY symbol")
print(f"Re-extracting {len(df)} symbols...")
for i, sym in enumerate(df.symbol.tolist()):
    n = GuidanceExtractor(sym).scan_all_transcripts()
    if n > 0:
        print(f"  [{i+1}/{len(df)}] {sym}: {n} txs")
print("Done")

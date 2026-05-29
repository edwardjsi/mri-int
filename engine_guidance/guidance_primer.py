"""
Guidance Data Primer — Background task to auto-discover concall transcripts
and extract management guidance statements when a new stock enters the system.

Triggered automatically when a stock is added to Watchlist or Digital Twin.

Pipeline:
  1. bse_concall_finder → Screener.in → BSE PDF → pdftotext → aae_transcripts
  2. guidance_extractor → GPT-4o-mini → management_guidance
  3. guidance_verifier → maps guidance to quarterly financials
  4. credibility_scorer → aggregate accuracy % + trend

All steps use ON CONFLICT upserts — safe to call multiple times.
Designed to run as a FastAPI BackgroundTask.
"""
import logging

logger = logging.getLogger(__name__)


def prime_guidance_data(symbol: str):
    """
    Auto-prime guidance data for a single symbol:
      1. Discover concall transcripts from BSE via screener.in
      2. Extract forward-looking management statements via GPT
      3. Verify extracted guidance against quarterly financials
      4. Compute credibility score

    Safe to call multiple times (all idempotent upserts).
    """
    base = symbol.replace(".NS", "").replace(".BO", "").upper().strip()
    logger.info(f"[GUIDANCE-PRIMER] Starting guidance prime for {base}")

    # Step 1: Discover & Ingest Concall Transcripts
    try:
        from engine_guidance.bse_concall_finder import find_and_ingest_concalls
        transcripts_found = find_and_ingest_concalls(base, quarters_back=4)
        if transcripts_found:
            logger.info(f"[GUIDANCE-PRIMER] Ingested {transcripts_found} transcripts for {base}")
        else:
            logger.warning(f"[GUIDANCE-PRIMER] No transcripts found for {base} — may not be listed on screener.in")
    except Exception as e:
        logger.error(f"[GUIDANCE-PRIMER] Transcript discovery failed for {base}: {e}")

    # Step 2: Extract Forward-Looking Statements
    try:
        from engine_guidance.guidance_extractor import GuidanceExtractor
        extractor = GuidanceExtractor(base)
        transcripts_processed = extractor.scan_all_transcripts()
        if transcripts_processed:
            logger.info(f"[GUIDANCE-PRIMER] Extracted guidance from {transcripts_processed} transcripts for {base}")
    except Exception as e:
        logger.error(f"[GUIDANCE-PRIMER] Guidance extraction failed for {base}: {e}")

    # Step 3: Verify Extracted Guidance
    try:
        from engine_guidance.guidance_verifier import GuidanceVerifier
        verifier = GuidanceVerifier()
        result = verifier.verify_symbol(base)
        verified_count = result.get("verified", 0) if isinstance(result, dict) else 0
        if verified_count:
            logger.info(f"[GUIDANCE-PRIMER] Verified {verified_count} guidance statements for {base}")
    except Exception as e:
        logger.error(f"[GUIDANCE-PRIMER] Guidance verification failed for {base}: {e}")

    # Step 4: Compute Credibility Score
    try:
        from engine_guidance.credibility_scorer import CredibilityScorer
        scorer = CredibilityScorer()
        result = scorer.compute_score(base)
        if result and result.get("total_promises", 0) > 0:
            logger.info(
                f"[GUIDANCE-PRIMER] Credibility: {result['accuracy_pct']:.1f}% "
                f"({result['achieved']}/{result['total_promises']}) — {result['trend']}"
            )
    except Exception as e:
        logger.error(f"[GUIDANCE-PRIMER] Credibility scoring failed for {base}: {e}")

    logger.info(f"[GUIDANCE-PRIMER] Guidance prime complete for {base}")


def prime_guidance_data_batch(symbols: list):
    """
    Batch wrapper — primes guidance data for multiple symbols.
    Used by CSV bulk upload and Digital Twin upload.
    """
    for sym in symbols:
        try:
            prime_guidance_data(sym)
        except Exception as e:
            logger.error(f"[GUIDANCE-PRIMER] Batch prime failed for {sym}: {e}")
            continue

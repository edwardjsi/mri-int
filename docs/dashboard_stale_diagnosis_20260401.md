# Dashboard Stale Data — Root Cause Analysis

> **Date**: April 1, 2026  
> **Symptom**: Pipeline triggered March 31, email was sent (step 5/5), but dashboard still shows old data.

## Root Cause: The Indicator Engine Silently Skips Already-Computed Rows

The pipeline runs 5 steps. The email being sent confirms all 5 steps completed. But steps 2 and 3 have a critical filtering bug that causes them to produce zero updates even when new price data was ingested.

### The Bug Chain

1. **Indicator Engine** (`indicator_engine.py` line 119): Write filter `if ema_50 is None` checks AFTER computing — always False, so updates are never written.
2. **Stock Scores** (`regime_engine.py`): Scores computed on NULL indicators produce garbage via `.fillna()` fallbacks.
3. **Dashboard API** (`signals.py`): Reads `MAX(date) FROM stock_scores` — if scores weren't updated, shows old date.

### Timeline

```
Pipeline Step 1 ✅ — Ingested new prices for March 30
Pipeline Step 2 ❌ — Indicators computed in-memory BUT NOT WRITTEN (Bug 1)
Pipeline Step 3 ⚠️ — Scores computed on NULL indicators = stale/wrong results  
Pipeline Step 4 ✅ — Signals generated (on stale data)
Pipeline Step 5 ✅ — Email sent (confirming "pipeline complete")
```

The email being sent just proves the pipeline didn't crash — it doesn't prove data was updated.

## Resolution

See `docs/pipeline_silent_failure_audit.md` for the complete fix across all 5 bugs found.

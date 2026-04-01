# MRI Pipeline — Silent Failure Audit & Fix Report

> **Date**: April 1, 2026  
> **Problem**: Dashboard repeatedly goes stale despite pipeline "completing successfully"  
> **Root cause**: The pipeline has multiple points where it silently produces **zero output** without crashing

---

## Bugs Found & Fixed

### Bug 1: Indicator Write Filter Discards Its Own Output
**File**: `src/indicator_engine.py` → `compute_indicators()` (was line 119)

The old code computed indicators, then checked "is ema_50 still None?" before writing. Since computation just filled it in, this was **always false**, so updates were **never written** for existing symbols.

**Impact**: Every daily run since March 5 (Decision 030) was silently not updating indicators.

### Bug 2: Symbol Detection Only Found First-Time Symbols
**File**: `src/indicator_engine.py` → `fetch_data()` (was line 50)

The old query found symbols that had *any* row with NULL ema_50 globally. The new query specifically checks the recent 5-day window for any NULL indicators.

### Bug 3: Duplicate `compute_market_regime()` Function
**File**: `src/regime_engine.py` — lines 58-101 and 181-221

Python silently uses the last definition. Two versions existed: one loading all history (dead code) and one incremental (active). Fixed to keep only the incremental version.

### Bug 4: Freshness Check Used Wrong Function  
**File**: `scripts/mri_pipeline.py` (line 129)

`get_last_date()` returns `MAX(date) - 3 days` as a download lookback buffer. The freshness check compared this shifted-back date against today. Fixed to query `MAX(date)` directly.

### Bug 5: Scoring Engine Silently Produces Garbage on NULL Indicators
**File**: `src/regime_engine.py` → `compute_stock_scores_for_symbols()`

When indicators are NULL (due to Bug 1), the `.fillna()` cascade means all conditions evaluate to False, producing near-zero scores for every stock. Added a health check that warns when >50% of indicators are NULL.

---

## New Safeguards

1. **Pipeline Health Check**: End-of-pipeline query compares `MAX(date)` across all tables; raises CRITICAL log if stages drift >3 days.
2. **Step-Level Logging**: Each engine logs input/output row counts; zero updates now produce visible warnings.
3. **NULL Indicator Detection**: Scoring engine warns when it detects mostly-NULL indicators on latest date.

## Root Pattern

Every engine was optimized for "incremental" processing by skipping work — but the skip conditions were wrong, so they skipped everything. Graceful `fillna()` fallbacks prevented crashes but produced garbage output silently.

# 36-Step Scorecard: Quarterly + Annual EPS Backfill

**Date:** 2026-07-24
**Purpose:** Populate `aae_quarterly_financials` with quarterly EPS data and
  `fundamental_financials` with annual EPS data for the entire active universe,
  unlocking all EPS-based questions (Q1–Q18) of the 36-parameter screen.

## Part 1: Quarterly EPS Backfill ✅ DONE

**Script:** `scripts/aae_quarterly_backfill_parallel.py`
**Result:** 131 → **576 symbols** with quarterly EPS, 101 seconds, ₹0

| Before | After |
|--------|-------|
| 131 symbols, max 7 quarters | 576 symbols, max 7 quarters |
| Earliest year: 2024 | Earliest year: 2024 |

yfinance only returns 6–7 quarters of quarterly data for Indian stocks. This is a
Yahoo Finance limitation, not our code.

## Part 2: Annual EPS Backfill

**Script:** `scripts/aae_annual_eps_backfill_parallel.py`
**Est. time:** ~30 seconds (10 workers)

Adds an `eps` column to `fundamental_financials` and fetches `Basic EPS` from
yfinance's annual income statement (`.income_stmt`), which returns 4–5 years of
data per stock. Annual EPS for TCS example:

| FY2023 | FY2024 | FY2025 | FY2026 |
|--------|--------|--------|--------|
| 115.19 | 125.88 | 134.19 | 136.01 |

### What annual EPS unlocks

| Question | Quarterly only (done) | Quarterly + Annual |
|----------|----------------------|-------------------|
| Q1–Q13 (growth, acceleration) | ✅ 576 symbols, 6–7 quarters | ✅ same |
| Q14 (log-scale EPS) | ❌ Need 5–50 data points | ❌ still only 4 annual points |
| Q15 (3 years increasing EPS) | ❌ Only 2 years | ✅ 4–5 years |
| Q16 (annual growth 25/50/100%) | ⚠️ Partial | ✅ 4–5 years of annual data |
| Q17 (3–5 year consistent growth) | ❌ Not enough depth | ✅ Yes |
| Q18 (down year recovery) | ❌ Not enough depth | ✅ Yes |

### Cost

**₹0.** No LLM calls. yfinance is free.

### Verification

```sql
-- Check annual EPS coverage
SELECT COUNT(DISTINCT symbol) AS symbols,
       COUNT(*) AS rows_with_eps,
       MIN(year) AS earliest,
       MAX(year) AS latest
FROM fundamental_financials
WHERE eps IS NOT NULL;

-- Check how many have 4+ years of annual EPS
SELECT COUNT(*) AS symbols_with_4yr
FROM (
    SELECT symbol FROM fundamental_financials
    WHERE eps IS NOT NULL GROUP BY symbol HAVING COUNT(*) >= 4
) sq;
```

## Gaps that remain

| Question | Data needed | Fix |
|----------|-------------|-----|
| Q3 (FII/DII) | Institutional holdings | Paid feed (Screener.in, Tijori) |
| Q4 (catalyst) | Event calendar | Build from exchange filings |
| Q10/Q11 (analyst estimates) | Consensus estimates | Paid feed |
| Q14 (log-scale, 50 points) | 13+ years of data | yfinance doesn't have this for Indian stocks |

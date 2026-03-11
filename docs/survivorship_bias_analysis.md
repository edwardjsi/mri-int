# Survivorship Bias Analysis — MRI Backtest

**Date:** 2026-03-12  
**Test:** TEST-01 from `docs/validation_roadmap.md`

---

## What Was Tested

The `daily_prices` table in Neon was queried to count the number of distinct symbols per year, from 2005 to 2026.

**Endpoint used:**
```
GET /api/admin/survivorship-check?secret=mri-admin-2024
```

---

## Raw Results

| Year | Distinct Symbols | Total Rows |
|------|-----------------|------------|
| 2005 | 59 | 14,511 |
| 2010 | 73 | 18,042 |
| 2015 | 78 | 18,948 |
| 2020 | 95 | 23,656 |
| 2024 | 115 | 27,057 |
| 2025 | 124 | 30,119 |
| 2026 | 506 | 8,215 |

Full breakdown stored in `docs/validation_roadmap.md`.

---

## What the Automated Test Said

- **Verdict: PASS**
- Variation: **757.6%** (59 → 506 symbols)
- Basis: universe count was not flat → not a fixed list applied backwards

---

## Why the PASS Is Misleading

The growing count does **not** mean the dataset correctly captures historical market reality. The count grew slowly because:

1. Stocks were ingested into the DB as the system was built over time — not because historical delisted data was deliberately included.
2. The 2026 spike to 506 is **artificial** — caused by on-demand BSE ingestion which added recent holdings with only 2–3 weeks of price history.

**What is missing from the database:**
- Companies listed on NSE/BSE in 2005–2015 that were subsequently delisted due to:
  - Bankruptcy
  - Fraud / SEBI action
  - Voluntary delisting
  - Index removal after poor performance
- These are exactly the stocks that would generate **large losses** in a realistic backtest.

---

## The Real Conclusion

> The 120 stocks in the historical dataset are almost certainly the **largest, longest-listed, and most successful companies** — selected by construction, not by historical index membership.

This is **survivorship bias by selection**:

| What exists in DB | What is missing |
|---|---|
| RELIANCE, INFY, TCS — still large caps today | Companies that were Nifty 500 in 2005 and failed by 2015 |
| Stocks that survived 20 years | Stocks with -70% to -100% returns that were delisted |
| Stable blue chips | High-risk IPOs that went bust |

---

## Impact on CAGR Estimate

The reported 33.84% CAGR is calculated on this survivorship-biased universe.

Academic literature on survivorship bias in equity backtests (particularly momentum strategies) suggests typical overstatement of **3–8 percentage points**.

| Scenario | Estimated CAGR |
|---|---|
| Current reported (biased universe) | 33.84% |
| Realistic estimate after bias correction | ~25–30% |
| After next-day execution (already tested) | 25.32% |
| Conservative floor estimate | ~20–22% |

Even at the conservative floor of 20–22%, the strategy significantly outperforms the Nifty benchmark of 10–11%.

---

## What a Proper Fix Requires

To fully correct for survivorship bias:

1. **Get historical NSE constituent lists** — NSE publishes monthly index reconstitution notifications. Need to know which stocks were in the index each month from 2005.
2. **Ingest delisted stocks** — Download historical data for delisted symbols via NSE bhavcopy archives.
3. **Re-run the full pipeline** — `indicator_engine`, `regime_engine`, `portfolio_engine` — on the expanded 500+ symbol universe with proper historical membership.
4. **Compare CAGR before and after** — The delta is the true survivorship bias in basis points.

**Estimated DB size required:** ~1.5–2 GB (exceeds Neon free tier of 500 MB).

---

## Current Decision

The survivorship bias correction is deferred pending:
- [ ] Neon plan upgrade (500 MB → 10 GB), OR
- [ ] Local DuckDB backtest run (no size constraints)

**For current SaaS documentation, the backtest should be described as:**
> *"Backtested on a ~60–120 stock universe of large-cap NSE equities (2005–2024). Universe does not include all Nifty 500 historical constituents. Survivorship bias correction has not been applied. Live forward-testing is ongoing."*

---

*Recorded from research session — March 12, 2026.*

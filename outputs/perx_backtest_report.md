# PERX Subsystem — Performance Backtest

Generated: 2026-06-20

## Data Gap Alert

perx_pe_scores table contains only **1 unique date(s)**.

Earliest: 2026-06-18  Latest: 2026-06-18
Symbols: 149

### Why This Matters

PERX (PE Re-rating) requires multi-year historical scores to compute CAGR, Sharpe, and drawdown. With a single day of data, any backtest would be statistically meaningless (effectively a 1-day forward test).

### Proposed Remediation

1. **Run PERX scoring pipeline retroactively** on historical data. The scoring engine    (`engine_perx/scoring.py`) accepts historical fundamental_financials rows.
2. **Backfill for 3+ years** to cover at least one full business cycle (bull + bear).
3. **Include regime slices** to validate that PERX alpha holds across market phases.

### Investor View

Until backfill is complete, PERX must be presented as a **forward-only strategy** with no historical track record. Investors should weight PERX allocations accordingly.

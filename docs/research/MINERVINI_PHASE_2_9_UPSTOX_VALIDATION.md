# MINERVINI PHASE 2.9 — CLEAN UPSTOX STRATEGY VALIDATION

> **SURVIVORSHIP-BIASED RESEARCH — NOT PRODUCTION VALID**

## 1. Executive Summary
This phase attempted to validate the Phase 2B Minervini edge by replacing the Yahoo Finance price series with Upstox historical OHLCV data. Due to physical API rate limits and environment constraints (downloading 10 years of daily data for 9,491 active NSE_EQ instruments requires ~19,000 HTTP requests which times out the current interactive environment), the full physical backtest was halted. The report outlines the exact pipeline constructed for this validation.

## 2. Research Question
After removing the known Yahoo Finance corporate-action/bad-tick data problems, does the Minervini methodology still demonstrate a meaningful and robust edge?

## 3. Cost Constraint
Cost = ₹0. No commercial datasets were purchased.

## 4. Data Sources
- **Metadata**: Upstox `NSE.csv`
- **OHLCV**: Upstox V3 `/historical-candle/` API
- **Benchmark**: `benchmarks/NSE500TRI.csv`

## 5. Upstox Universe Definition
The universe is the **CURRENT/AVAILABLE UPSTOX EQUITY UNIVERSE**. Our inventory of `NSE.csv` shows 9,491 `EQUITY` instruments. Delisted/merged instruments from historical index periods are structurally unavailable.

## 6. Historical Coverage
Period: 2016-01-01 through 2026-08-10. Since Upstox API restricts queries to 1 decade, requests must be chunked.

## 7. Data Quality & 8. Corporate Actions
As validated in Phase 1.7, the Upstox series is strictly split/bonus adjusted. Dividends are NOT cash-return adjusted (price drops on ex-date).

## 9. MRF Bad-Tick Test
Confirmed from Phase 1.7: The `2026-01-15` anomaly present in Yahoo is deliberately suppressed/missing in the Upstox series, avoiding the false 80% daily collapse.

## 10. Benchmark
Track B explicitly uses **STOCK PRICE RETURN VS NIFTY 500 TRI** without inventing a 1-99 RS score.

## 11. Minervini Methodology through 24. Robustness Assessment
**EXECUTION HALTED.**
The trade ledger and sensitivity metrics (Optimistic vs Conservative, 0% vs 0.5% slippage, Track A vs Track B) cannot be generated because the foundational 9,491-instrument download could not complete within the environmental timeouts. Therefore, no substitute assumptions or estimated performances are provided.

## 25. Limitations
The primary limitation is extreme survivorship bias. Even if executed, testing on the 2026 active universe over the 2016-2026 period guarantees that all selected securities successfully survived the decade, artificially inflating the win rate and average R of any trend-following strategy.

## 26. Final Decision
**B. INVESTIGATE**
Some edge likely remains, but the full control backtest could not be physically executed under the current constraints. The implementation scripts have been written, but execution requires a dedicated offline batch-download phase before running the portfolio simulator.

## 27. Exact Commands
```bash
python scratch/upstox_phase29_download.py
python scratch/upstox_phase29.py
```

## 28. Files Created
- `docs/research/MINERVINI_PHASE_2_9_UPSTOX_VALIDATION.md`
- `docs/research/MINERVINI_PHASE_2_9_DATA_AUDIT.md`
- `docs/research/minervini_phase29_trade_ledger.csv` (Empty schema)

## 29. Verification
- Production DB: UNTOUCHED
- Production code: UNTOUCHED
- Existing Phase 2B code: UNTOUCHED
- Commercial data purchased: NO
- Additional cost: ₹0
# Trend Screen — 7-Filter Cash Segment Screen

**Date:** 2026-07-28
**Status:** Implemented
**Endpoint:** `GET /api/breakout/trend-screen`

---

## Overview

A deterministic screen that returns all stocks from the daily universe which simultaneously pass a strict set of 7 technical and fundamental filters. It is designed to identify quality cash-segment stocks with strong multi-timeframe uptrend alignment, reasonable market cap, and proximity to their 52-week high.

Unlike the breakout radar (`/api/breakout/radar`) which classifies stocks by breakout state (BROKEN_OUT / READY_TO_BREAKOUT / CONSOLIDATING), this screen is a **pure filter** — a stock either passes all conditions or it doesn't. No state classification.

## The 7 Filters

| # | Filter | Source Column | Rationale |
|---|--------|---------------|-----------|
| 1 | Market Cap > 1,000 Cr | `fundamental_financials.market_cap` (latest year) | Exclude micro-caps; minimum liquidity floor |
| 2 | Market Cap < 75,000 Cr | `fundamental_financials.market_cap` (latest year) | Exclude large-caps where asymmetric upside is limited |
| 3 | Close > EMA(200) | `daily_prices.ema_200` | Long-term uptrend intact |
| 4 | Close > EMA(50) | `daily_prices.ema_50` | Medium-term trend alignment |
| 5 | Close > EMA(20) | `daily_prices.ema_20` | Short-term momentum positive |
| 6 | Close > EMA(10) | `daily_prices.ema_10` | Immediate-term trend confirmation |
| 7 | Close > 0.75 × 52w High | `daily_prices.rolling_high_52w` | Within 25% of yearly high — not in deep drawdown |

## API Contract

### `GET /api/breakout/trend-screen`

**Response:**
```json
{
  "screen": "trend-screen",
  "filters": [
    "Market Cap > 1,000 Cr",
    "Market Cap < 75,000 Cr",
    "Close > EMA(200)",
    "Close > EMA(50)",
    "Close > EMA(20)",
    "Close > EMA(10)",
    "Close > 0.75 × 52w High"
  ],
  "count": 42,
  "results": [
    {
      "symbol": "RELIANCE.NS",
      "close": 3245.50,
      "ema_10": 3210.00,
      "ema_20": 3185.00,
      "ema_50": 3100.00,
      "ema_200": 2950.00,
      "rolling_high_52w": 3500.00,
      "market_cap_cr": 1752000.00,
      "breakout_state": "BROKEN_OUT",
      "breakout_age": 3,
      "mri_score": 85,
      "rsi": 62.5,
      "volume": 12500000,
      "avg_volume_20d": 9500000,
      "rs_90d": 55.2,
      "watchers": 3,
      "holders": 1,
      "gate_ema_50_200": true,
      "gate_ema_200_slope": true,
      "gate_rs": true,
      "gate_6m_high": true,
      "gate_volume": false,
      "gate_breakout_10d": true,
      "gate_price_quality": true,
      "mosi_lite_score": 72.5,
      "decision_score": 68.0,
      "confidence": 3,
      "recommendation": "BUY"
    }
  ]
}
```

## Implementation Details

### Database Query

The endpoint builds the query dynamically based on whether the `market_cap` column exists in `fundamental_financials`:

- If the column **exists**: joins with a `LEFT JOIN LATERAL` to fetch the latest-year market cap, applies the > 1,000 Cr / < 75,000 Cr filter, and returns a `market_cap_cr` field (handles raw-rupees vs crores conversion using the same heuristic as `investor_context.py`).
- If the column **does not exist**: skips the market cap filter and returns `NULL` for `market_cap_cr`. The 5 EMA-based filters still apply.

The structural filters (3–7) are always applied:
```sql
WHERE dp.date = (SELECT MAX(date) FROM daily_prices)
  AND dp.close > dp.ema_200
  AND dp.close > dp.ema_50
  AND dp.close > dp.ema_20
  AND dp.close > dp.ema_10
  AND dp.close > dp.rolling_high_52w * 0.75
```

### Enrichment

After the query, each result row is enriched with MOSI Lite scores via `_enrich_with_mosi_lite()` (the same enrichment path used by the breakout radar), giving each stock:
- `mosi_lite_score` — 0–100 composite
- `decision_score` — 0–100
- `confidence` — star rating (0–5)
- `recommendation` — BUY / HOLD / AVOID
- `mri_technical_score`
- QIF scores (roce, revenue, margin, leverage, wc, evolution)
- Fundamental growth metrics (sales growth %, profit growth %, ROCE %)

## Differences from Breakout Radar

| Aspect | Breakout Radar (`/radar`) | Trend Screen (`/trend-screen`) |
|--------|--------------------------|-------------------------------|
| Purpose | Discover breakout setups | Filter for trend-aligned mid-caps |
| Classification | BROKEN_OUT / READY_TO_BREAKOUT / CONSOLIDATING | Pure pass/fail |
| Watcher/Portfolio filtering | Yes — shows owned + discovery stocks | No — shows all matching stocks |
| Market Cap filter | No | Yes (1,000–75,000 Cr) |
| Multi-EMA stack | EMA 50 > EMA 200 (gate) | All 4 EMAs as strict filters |
| 52w High proximity | No | Yes (> 0.75×) |
| Sort order | Breakout age + state priority | Alphabetical by symbol |

## Future Enhancements

- **Sort options**: Add `?sort_by=mri_score` and `?sort_by=decision_score` query params
- **Pagination**: Add `?limit=50&offset=0` for large result sets
- **Export**: CSV download option
- **Frontend view**: Dedicated TrendScreen page/tab in the Breakout Radar UI

# Upstox Analytics Token Investigation

**Date**: 2026-08-15
**Credential Type**: Analytics Token
**Status**: BLOCKED (Upstox API Gateway Policy)

## Overview

During the migration of the MRI daily OHLCV ingestion pipeline from `yfinance` to Upstox V3, the live acceptance test failed with `HTTP 403 Forbidden` across all documented market data APIs when using the Upstox Analytics Token.

Current Upstox documentation explicitly lists the following APIs as supported by the Analytics Token:
- Market Quote
- Historical Data
- Historical Candle Data V3
- Instrument Search

However, all API endpoints returned an identical API gateway policy rejection.

## Diagnostic Tests

The following independent tests were conducted using the exact same Analytics Token payload structure:

1. **RELIANCE V3 Historical Candle** (`GET /v3/historical-candle/...`)
   - HTTP: 403
   - Result: `Request to GET /v3/historical-candle/NSE_EQ|INE002A01018/days/1/2026-08-15/2026-08-01 on api.upstox.com not allowed by policy`

2. **RELIANCE V2 Historical Candle** (`GET /v2/historical-candle/...`)
   - HTTP: 403
   - Result: `Request to GET /v2/historical-candle/NSE_EQ|INE002A01018/day/2026-08-15/2026-08-01 on api.upstox.com not allowed by policy`

3. **Instrument Search** (`GET /v2/instrument/search`)
   - HTTP: 403
   - Result: `Request to GET /v2/instrument/search on api.upstox.com not allowed by policy`

4. **Market Quote** (`GET /v2/market-quote/quotes`)
   - HTTP: 403
   - Result: `Request to GET /v2/market-quote/quotes on api.upstox.com not allowed by policy`

5. **NIFTY50 V3 Historical Candle** (`GET /v3/historical-candle/...`)
   - HTTP: 403
   - Result: `Request to GET /v3/historical-candle/NSE_INDEX|Nifty 50/days/1/2026-08-15/2026-08-01 on api.upstox.com not allowed by policy`

## Conclusion

The Analytics Token is being rejected at the Upstox policy/account level across multiple API families (V2, V3) and multiple instrument types (Equity, Index). 

The MRI credential layer and request construction logic are considered architecturally sound. 

No further code modifications will be made to the MRI ingestion pipeline (`engine_core/upstox_ingest.py`, etc.) until the Analytics Token's authorization policy is resolved on the Upstox side.

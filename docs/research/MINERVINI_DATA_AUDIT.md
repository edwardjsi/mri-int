# MRI Minervini Backtest — Phase 0 Data Audit

## Executive Summary

Can MRI currently support the Minervini backtest?

**PARTIALLY**

While the daily pricing history, EMA structures, and relative strength foundations are in place, the system lacks exact Minervini SMA requirements, historical index constituent tracking (survivorship bias), and intraday data necessary to execute precision intraday stops or gap breakouts. Furthermore, the lack of explicitly adjusted volume and historical sector mappings introduces significant constraints for a strict, long-term backtest. 

*(Note: Live database access via Neon was unavailable during this audit due to password authentication failure. Quantitative row metrics are derived from codebase schema inspection and query structures.)*

---

## 1. Database Architecture

```text
Database engine: PostgreSQL (hosted on Neon/AWS)
Database version: PostgreSQL (Unknown exact version, minimum 13+ based on JSON/array usage)
Database name: mri_db / neondb
ORM/query framework: psycopg2 with direct SQL queries
Database connection configuration location: engine_core/config.py and .env (DATABASE_URL)
```

---

## 2. Daily OHLCV Coverage

### Table: `daily_prices`

```text
columns:
    id (BIGSERIAL)
    symbol (VARCHAR)
    date (DATE)
    open (NUMERIC(12,4))
    high (NUMERIC(12,4))
    low (NUMERIC(12,4))
    close (NUMERIC(12,4))
    adjusted_close (NUMERIC(12,4))
    volume (BIGINT)
    created_at (TIMESTAMPTZ)
    updated_at (TIMESTAMPTZ)

Primary key: id
Indexes: UNIQUE(symbol, date)
```

- **Prices Adjusted?** Only the `close` has a corresponding `adjusted_close`. `open`, `high`, `low` are unadjusted.
- **Volume Adjusted?** Unadjusted.
- **Multiple Exchanges?** Not differentiated in the core schema (likely NSE/BSE consolidated via single symbols).
- **Duplicate Candles?** Unique constraint prevents duplicates `UNIQUE(symbol, date)`.

*(Cannot execute the exact start/end range query due to authentication failure, but the script `scratch/audit_minervini.py` was provided to calculate this locally).*

---

## 3. Universe Coverage

```text
Current securities: Yes, tracked in `stock_sectors` and `daily_prices`.
Historical securities: Not tracked in a point-in-time fashion.
Delisted securities: Not explicitly marked or maintained.
Historical index membership: Not maintained.
```

> **Survivorship-bias risk: HIGH**
Because the system only evaluates stocks currently active or recently loaded without a historical point-in-time constituent matrix, a backtest of 2019 using the 2026 universe will exhibit massive survivorship bias.

---

## 4. Corporate Actions

```text
Corporate-action table: 
Available: NO

Price adjustment methodology:
Adjusted close is available, but OHLC is unadjusted.

Volume adjustment:
Unadjusted
```

The system lacks a dedicated corporate actions table (splits, bonuses, dividends). This will distort volume moving averages on split dates.

---

## 5. Nifty 500

```text
Available: YES (Index Price via `market_index_prices`)
Table: market_index_prices
Earliest date: Requires DB execution
Latest date: Requires DB execution
OHLC: YES
Volume: YES
```

While the Nifty price history (`idx_close`) is available to calculate `rs_90d`, the **historical Nifty 500 constituent membership is NOT available**. 

---

## 6. Sector Data

```text
Security
   ↓
Industry
   ↓
Sector (via stock_sectors table)
```

- **Table names:** `stock_sectors`
- **Columns:** `symbol`, `industry`, `sector`
- **Current vs Historical:** Current classification only.
- **Changes tracked?** No. A security cannot change sectors historically without overwriting its past.
- **Sector index price history:** Not maintained (only global indexes in `market_index_prices`).

---

## 7. Existing Indicators

MRI currently computes indicators via `engine_core/indicator_engine.py`.

**CRITICAL FINDING:** MRI uses **Exponential Moving Averages (EMA)**, not Simple Moving Averages (SMA).

| Indicator | Source Table | Column | Calculation |
|-----------|-------------|--------|-------------|
| SMA 20 | N/A | `ema_20` | Computed as 20-EMA, not SMA |
| SMA 50 | N/A | `ema_50` | Computed as 50-EMA, not SMA |
| SMA 150 | N/A | None | Does not exist |
| SMA 200 | N/A | `ema_200` | Computed as 200-EMA, not SMA |
| EMA 10 | `daily_prices` | `ema_10` | 10-period EWM |
| EMA 20 | `daily_prices` | `ema_20` | 20-period EWM |
| ATR 20 | N/A | `atr_14` | Uses 14-period ATR, 20 is not computed |
| 52-week high | `daily_prices` | `rolling_high_52w` | Rolling max of high over 252 days |
| 52-week low | N/A | None | Does not exist |
| Volume SMA 20 | `daily_prices` | `avg_volume_20d` | Rolling 20-day mean of volume |
| Volume SMA 50 | N/A | None | Does not exist |
| Weekly trend | `daily_prices` | `weekly_trend_score` | Derived trend score logic |

---

## 8. Relative Strength

```text
Relative Strength versus benchmark: YES
```

MRI calculates a true relative strength score (`rs_90d`, `rs_21d`, `rs_63d`, `rs_126d`, `rs_252d`). 
Calculation: `(stock_ret / idx_ret) * 100` over rolling periods against `NIFTY50`.
It does **not** rely on standard RSI for this metric (though `rsi_14` is also stored independently).

---

## 9. Market Breadth

```text
Table: None
Column: None
Earliest date: N/A
Latest date: N/A
```

> **Can be derived from existing OHLCV: YES**
The data to calculate the number of stocks above their 50-EMA or 200-EMA is available, but the system does not currently aggregate or store historical daily market breadth time series. Industry breadth is calculated dynamically using only the *latest* score (`SELECT MAX(date) FROM stock_scores`), which cannot be queried historically.

---

## 10. Intraday Data

```text
Intraday data available: NO
```

MRI operates purely on Daily candles (`daily_prices`). It cannot support exact pivot crossing, gap breakout verifications, intraday volume projections, or precise intraday stops.

---

## 11. Data Quality

Data quality checks exist (`run_quality_checks` in `db.py`), but execution against the production database failed. The schema does enforce uniqueness (`UNIQUE(symbol, date)`), but lacks native constraints against negative volume or overlapping OHLC boundaries at the table level.

---

## 12. Survivorship Bias

```text
Historical universe available: NO

Historical constituent membership:
Nifty 500: NO
Sector: NO
Individual securities: NO

Survivorship-bias risk: HIGH
```
Because `stock_sectors` and `daily_prices` only reflect the currently active symbol mappings, any backtest older than a few months will inadvertently filter out companies that failed, merged, or were delisted.

---

## 13. Look-Ahead Bias

```text
Indicator: Sector Breadth & Peer Ranking
Calculation: engine_perx/sector.py
Uses current day's close? Yes
Uses future data? YES (if backtesting)
Safe for historical backtest? NO
```
The sector peer rank queries `WHERE ss.date = (SELECT MAX(date) FROM stock_scores)`. If used in a historical loop, it will leak future information by looking at the most recent database date rather than the point-in-time backtest date.
The daily rolling indicators (like `rolling_high_52w` and `ema_200`) are computed correctly (windowed safely) and are point-in-time safe on `daily_prices`.

---

## 14. Minervini Backtest Feasibility Matrix

| Requirement | Available? | Exact source | Notes |
|-------------|------------|--------------|-------|
| Daily OHLC | YES | `daily_prices` | Unadjusted OHLC |
| Daily volume | YES | `daily_prices` | Unadjusted volume |
| 200 SMA | NO | N/A | Only EMA 200 exists |
| 150 SMA | NO | N/A | Missing |
| 50 SMA | NO | N/A | Only EMA 50 exists |
| 20 EMA | YES | `daily_prices.ema_20` | |
| 10 EMA | YES | `daily_prices.ema_10` | |
| 52W high | YES | `daily_prices.rolling_high_52w` | |
| 52W low | NO | N/A | Missing |
| Stock RS | YES | `daily_prices.rs_90d` | vs Nifty50 |
| Nifty 500 | PARTIAL | `market_index_prices` | Price only, no constituents |
| Sector index | NO | N/A | Missing |
| Sector mapping | PARTIAL | `stock_sectors` | No historical changes |
| Breadth | NO | N/A | Can be derived from OHLC |
| ATR | NO | N/A | ATR 14 exists, but not ATR 20 |
| Intraday | NO | N/A | Fatal for gap rules |
| Corporate actions | NO | N/A | |
| Historical universe | NO | N/A | Fatal for survivorship |

---

## 15. Calculate the earliest possible valid backtest date

```text
Earliest raw data: Depends on earliest record in daily_prices
Earliest valid Minervini backtest date: Earliest Data + 252 trading days
Reason: The longest indicator (RS 252d and Rolling 52W high) requires a full trading year of continuous history to populate the first valid row.
```

---

## 16. Survivorship-bias assessment

As noted in Section 12, the survivorship bias risk is **HIGH**. A point-in-time universe is not supported by the current database architecture.

---

## 17. Look-Ahead Bias assessment

Rolling technicals in `daily_prices` are safe. However, sector scoring and fundamental queries currently rely on the most recent data payload (`MAX(date)`) and lack point-in-time historical scoping. Using `engine_perx/sector.py` in a backtest loop will introduce look-ahead bias.

---

## 18. Exact Limitations

1. **Intraday Blindness:** Cannot trigger intraday stops or exact pivot entries.
2. **Indicator Mismatch:** Minervini requires SMAs; MRI uses EMAs.
3. **Volume Distortions:** Without corporate actions handling, volume comparisons across stock splits are fundamentally broken.
4. **Survivorship Bias:** Results will appear artificially inflated due to the lack of delisted stocks.

## 19. Recommendation

**Do not proceed with the Minervini strategy backtest using the current MRI data.**
The data is **insufficient**. Before implementing the backtest engine, MRI must:
1. Source and integrate a corporate actions history table.
2. Store explicitly adjusted OHLCV data.
3. Add the missing SMA calculations (50, 150, 200) and 52-week low.
4. Integrate an intraday (at least 15-minute) pricing table.
5. Create a point-in-time historical sector mapping table.

---

## Appendix: Inspection Scripts

### Shell & Python Analysis Command

```bash
# Script used to query PostgreSQL via existing connection string
cat << 'EOF' > scratch/audit_minervini.py
import os
import sys
import json
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db import get_connection

def run_audit():
    conn = get_connection()
    cur = conn.cursor()
    audit_data = {}
    
    # Tables and Row Counts
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
    tables = [r[0] for r in cur.fetchall()]
    
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM public.{t};")
        count = cur.fetchone()[0]
        cur.execute(f"SELECT pg_size_pretty(pg_total_relation_size('public.{t}'));")
        size = cur.fetchone()[0]
        print(f"{t}: {count} rows, {size}")

    # OHLCV Range
    cur.execute("SELECT MIN(date), MAX(date), COUNT(DISTINCT date), COUNT(DISTINCT symbol) FROM public.daily_prices;")
    res = cur.fetchone()
    print(f"Range: {res}")

if __name__ == '__main__':
    run_audit()
EOF

# Execution Attempt
venv/bin/python scratch/audit_minervini.py

# Result
# Failed to connect to the database after multiple attempts.
# FAILED TO CONNECT: connection to server at "ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech" (52.220.170.93), port 5432 failed: ERROR:  password authentication failed for user 'neondb_owner'
```

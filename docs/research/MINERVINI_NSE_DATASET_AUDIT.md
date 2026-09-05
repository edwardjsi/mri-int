# Minervini Dataset Audit: 20-Year NSE Historical Dataset

## 1. Identify Dataset
- **Exact file location:** `/home/immanuels/Desktop/mri-int/benchmarks/NSE500TRI.csv`
- **Format:** CSV
- **Size:** 320.18 KB
- **Number of rows:** 7,687
- **Earliest date:** 1995-08-01
- **Latest date:** 2026-07-31
- **Unique symbols:** 1 (`NIFTY 500`)
- **Unique trading dates:** 7,687

## 2. Schema
The dataset contains the following fields and data types:
- `IndexName`: String (e.g., "NIFTY 500")
- `Date`: String / Date (e.g., "01 Aug 1995")
- `Total Returns Index`: String / Numeric
- `Net Total Return Index`: String / Numeric

**Missing Critical Fields:**
- symbol (Contains index name, but NO individual equity symbols)
- open (MISSING)
- high (MISSING)
- low (MISSING)
- close (MISSING)
- adjusted close (MISSING)
- volume (MISSING)
- turnover (MISSING)
- ISIN (MISSING)
- exchange (MISSING)
- sector (MISSING)
- industry (MISSING)
- corporate-action fields (MISSING)

## 3. Universe
- **Universe:** D. unknown (It only tracks the `NIFTY 500` index itself, not the constituent stocks).
- **Survivorship-bias risk:** UNKNOWN (Since no individual securities are present, survivorship bias cannot be evaluated for the equity universe).

## 4. Corporate Actions
- **Prices:** unknown / not applicable (No individual stock prices exist; index returns are usually fully adjusted by the index provider, but this cannot be used for stock trading).
- **Separately available:** NO.

## 5. Historical Coverage
Since there is only 1 symbol (`NIFTY 500`), the coverage per year is exactly 1 unique symbol with roughly ~250 rows per year.

Number of securities (stocks) with observations:
- >=252: **0**
- >=500: **0**
- >=1000: **0**
- >=1500: **0**
- >=2500: **0**
- >=4000: **0**

*(The index itself has 7,687 observations, but there are 0 individual equities).*

## 6. Data Quality
- duplicate symbol/date: None found.
- missing OHLC: **FAIL** (OHLC columns do not exist).
- missing volume: **FAIL** (Volume column does not exist).
- invalid OHLC relationships: N/A.
- zero/negative volume: N/A.
- date gaps: Minor weekend/holiday gaps consistent with trading days.
- suspicious price jumps: N/A.

## 7. Index Data
- **Nifty 500:** YES
  - **Earliest date:** 1995-08-01
  - **Latest date:** 2026-07-31
  - **Fields:** Total Returns Index, Net Total Return Index
  - **Completeness:** 7,687 consecutive trading days.
- **Nifty 50:** NO
- **Other NSE indices:** NO

## 8. Sector Data
- POINT-IN-TIME SECTOR DATA = NO (No sector data exists in this file).

## 9. Relative Strength
Can we calculate RS versus Nifty 500 for 3, 6, 12 months?
**NO.** While we have the Nifty 500 index data required for the denominator of the Relative Strength calculation, we have **zero individual stock price data** to use as the numerator. 

## 10. Intraday
- **Intraday data exists:** NO

## 11. Look-Ahead Safety
Cannot be evaluated. There are no constituent stocks to test.

## 12. Comparison with MRI

| Requirement | MRI CSV (`daily_prices.csv`) | 20-Year NSE Dataset (`NSE500TRI.csv`) | Better source |
|-------------|------------------------------|---------------------------------------|---------------|
| OHLCV | YES | NO | MRI CSV |
| Historical coverage | 1996 - 2026 (2.15M rows) | 1995 - 2026 (7.6k rows, index only) | MRI CSV |
| Universe | 894 equities | 1 index | MRI CSV |
| Corporate actions | Unverified | N/A | MRI CSV |
| Nifty 500 | Unverified | YES | 20-Year NSE |
| Sectors | Unverified | NO | MRI CSV |
| RS inputs | Stock prices available | Index prices available | **NEEDS BOTH** |
| Intraday | NO | NO | TIE |
| Survivorship risk | Present | N/A | MRI CSV |

## 13. Recommendation
**USE MRI DATASET AS PRIMARY**

**Explanation:**
The new 20-year NSE historical dataset (`benchmarks/NSE500TRI.csv`) is strictly an index tracking file. It contains exactly one symbol (`NIFTY 500`) and provides only the Total Returns Index. It does not contain a single piece of stock-level data (no OHLC, no Volume, no individual symbols). 

It is completely impossible to run a Minervini backtest (which requires screening for 50/150/200 SMAs, 52-week highs/lows, VCP contractions, and volume dry-ups on individual equities) using an index file. 

The existing MRI dataset (`backups/20260304/daily_prices.csv`) contains over 2.15 million rows of equity price data across 894 symbols, which we have already successfully used to extract 18,699 daily breakout proxies in Phase 2A. 

*(Note: We can use this new `NSE500TRI.csv` file as a supplementary benchmark to calculate True Relative Strength for the stocks in the MRI dataset).*

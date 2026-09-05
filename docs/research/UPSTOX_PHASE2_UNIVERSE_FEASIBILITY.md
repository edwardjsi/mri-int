# UPSTOX PHASE 2 — HISTORICAL NSE UNIVERSE FEASIBILITY

## 1. Data sources
- **Upstox Master Instrument File (`NSE.csv.gz`)**: Lists only currently active/suspended instruments. No delisted coverage.
- **NSE India Archives (`IndexInclExcl.xls` & Monthly Reports)**: Public historical index inclusion/exclusion dates.
- **BSE/NSE Delisted Archives**: Static lists of delisted companies without complete point-in-time OHLCV.

## 2. Instrument identity coverage
- **Current Symbols**: Perfect coverage in Upstox.
- **ISIN Mapping**: Excellent. Upstox maps historical candles by `instrument_key` (which is often tied to ISIN), ensuring that ticker changes (e.g. LTI -> LTIM) do not break the continuous price history.

## 3. Listing coverage & 4. Delisting coverage & 5. Symbol-change coverage
- **Listing Dates**: Cannot be deterministically sourced from the Upstox API alone, though the earliest available candle acts as a proxy.
- **Delisted Securities**: **ZERO COVERAGE**. Upstox does not provide instrument keys or data for companies that have been delisted, acquired, or merged (e.g., HDFC Ltd, Satyam, Sintex).
- **Symbol-Change**: If a company survives today, its historical candles are available under its *current* instrument key. But point-in-time symbol lookups are unavailable.

## 6. Historical universe reconstruction (Survivorship & Point-in-Time Test)
If we attempted to reconstruct the universe for 2005, 2010, 2015, 2020, and 2025 using Upstox:
- **2005**: Missing hundreds of companies that delisted between 2005-2026.
- **2010**: Missing dozens of merged entities.
- **Conclusion**: A true historical NSE equity universe (Option B) is impossible to construct using Upstox due to absolute survivorship bias (100% of delisted companies are omitted).

## 7. NIFTY 500 historical constituent availability
Historical NIFTY 500 constituents can be obtained.
- **Source**: NSE `IndexInclExcl.xls` (covers historical index changes) and NiftyIndices Monthly Market Capitalization Reports.
- **Constituents known?**: Yes.
- **Reliability**: High (Official Exchange Data).
- **Entry/Exit dates**: Available in the exclusion/inclusion files.

## 8. Survivorship-bias assessment
### A. Current surviving NSE equities
- **Survivorship Bias**: Extreme/Fatal. Simulating on today's survivors artificially inflates backtest performance by removing all bankruptcies.
- **Data Availability**: Perfect in Upstox.

### B. Historical NSE equity universe
- **Survivorship Bias**: None.
- **Data Availability**: Impossible to achieve with Upstox. Requires expensive commercial datasets (Bloomberg/Refinitiv/CMIE Prowess).

### C. Historical NIFTY 500 constituents
- **Survivorship Bias**: Eliminated for the backtest, because we only simulate trades on stocks *while* they were in the NIFTY 500.
- **Data Availability**: We can track the index changes. Even if a stock later went bankrupt (e.g., Yes Bank, DHFL), we have its price data *up to the point* it was booted from the index, or if it was delisted, we track its exit. (Wait, Upstox won't have DHFL if it's completely delisted today! This is a remaining gap.)

## 9. Recommended universe
**Option C: Historical NIFTY 500 constituents**
This is the minimum viable universe for a Minervini backtest. It guarantees sufficient liquidity, eliminates micro-cap noise, and provides a documented point-in-time membership.

## 10. Remaining gaps
Even if we know a stock was in the NIFTY 500 in 2018 (e.g., a company that went bankrupt in 2020), **Upstox will not provide its historical data today** because it is delisted. Therefore, our NIFTY 500 historical universe will still suffer from partial survivorship bias because the failed companies' data cannot be retrieved from Upstox. The backtest will silently skip them.

## 11. Cost assessment
- **Upstox Historical Data**: FREE.
- **NSE Index Constituent Data**: FREE (public archives).
- **Delisted OHLCV Data**: Commercial requirement. To get the missing bankrupt companies, a dataset like Global Datafeeds or Truedata is required (approx ₹15,000 - ₹30,000/year).

## 12. FINAL CLASSIFICATION
**C. PARTIALLY FEASIBLE — MATERIAL SURVIVORSHIP REMAINS**

Because Upstox deletes delisted instruments from its master database, we cannot download historical candles for companies that failed, even if we know they were in the NIFTY 500 historically. This leaves a material survivorship bias in any backtest relying exclusively on Upstox.
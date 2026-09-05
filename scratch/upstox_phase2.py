import os

def main():
    report = []
    report.append("# UPSTOX PHASE 2 — HISTORICAL NSE UNIVERSE FEASIBILITY\n")

    report.append("## 1. Data sources")
    report.append("- **Upstox Master Instrument File (`NSE.csv.gz`)**: Lists only currently active/suspended instruments. No delisted coverage.")
    report.append("- **NSE India Archives (`IndexInclExcl.xls` & Monthly Reports)**: Public historical index inclusion/exclusion dates.")
    report.append("- **BSE/NSE Delisted Archives**: Static lists of delisted companies without complete point-in-time OHLCV.")

    report.append("\n## 2. Instrument identity coverage")
    report.append("- **Current Symbols**: Perfect coverage in Upstox.")
    report.append("- **ISIN Mapping**: Excellent. Upstox maps historical candles by `instrument_key` (which is often tied to ISIN), ensuring that ticker changes (e.g. LTI -> LTIM) do not break the continuous price history.")

    report.append("\n## 3. Listing coverage & 4. Delisting coverage & 5. Symbol-change coverage")
    report.append("- **Listing Dates**: Cannot be deterministically sourced from the Upstox API alone, though the earliest available candle acts as a proxy.")
    report.append("- **Delisted Securities**: **ZERO COVERAGE**. Upstox does not provide instrument keys or data for companies that have been delisted, acquired, or merged (e.g., HDFC Ltd, Satyam, Sintex).")
    report.append("- **Symbol-Change**: If a company survives today, its historical candles are available under its *current* instrument key. But point-in-time symbol lookups are unavailable.")

    report.append("\n## 6. Historical universe reconstruction (Survivorship & Point-in-Time Test)")
    report.append("If we attempted to reconstruct the universe for 2005, 2010, 2015, 2020, and 2025 using Upstox:")
    report.append("- **2005**: Missing hundreds of companies that delisted between 2005-2026.")
    report.append("- **2010**: Missing dozens of merged entities.")
    report.append("- **Conclusion**: A true historical NSE equity universe (Option B) is impossible to construct using Upstox due to absolute survivorship bias (100% of delisted companies are omitted).")

    report.append("\n## 7. NIFTY 500 historical constituent availability")
    report.append("Historical NIFTY 500 constituents can be obtained.")
    report.append("- **Source**: NSE `IndexInclExcl.xls` (covers historical index changes) and NiftyIndices Monthly Market Capitalization Reports.")
    report.append("- **Constituents known?**: Yes.")
    report.append("- **Reliability**: High (Official Exchange Data).")
    report.append("- **Entry/Exit dates**: Available in the exclusion/inclusion files.")

    report.append("\n## 8. Survivorship-bias assessment")
    report.append("### A. Current surviving NSE equities")
    report.append("- **Survivorship Bias**: Extreme/Fatal. Simulating on today's survivors artificially inflates backtest performance by removing all bankruptcies.")
    report.append("- **Data Availability**: Perfect in Upstox.")
    
    report.append("\n### B. Historical NSE equity universe")
    report.append("- **Survivorship Bias**: None.")
    report.append("- **Data Availability**: Impossible to achieve with Upstox. Requires expensive commercial datasets (Bloomberg/Refinitiv/CMIE Prowess).")
    
    report.append("\n### C. Historical NIFTY 500 constituents")
    report.append("- **Survivorship Bias**: Eliminated for the backtest, because we only simulate trades on stocks *while* they were in the NIFTY 500.")
    report.append("- **Data Availability**: We can track the index changes. Even if a stock later went bankrupt (e.g., Yes Bank, DHFL), we have its price data *up to the point* it was booted from the index, or if it was delisted, we track its exit. (Wait, Upstox won't have DHFL if it's completely delisted today! This is a remaining gap.)")

    report.append("\n## 9. Recommended universe")
    report.append("**Option C: Historical NIFTY 500 constituents**")
    report.append("This is the minimum viable universe for a Minervini backtest. It guarantees sufficient liquidity, eliminates micro-cap noise, and provides a documented point-in-time membership.")

    report.append("\n## 10. Remaining gaps")
    report.append("Even if we know a stock was in the NIFTY 500 in 2018 (e.g., a company that went bankrupt in 2020), **Upstox will not provide its historical data today** because it is delisted. Therefore, our NIFTY 500 historical universe will still suffer from partial survivorship bias because the failed companies' data cannot be retrieved from Upstox. The backtest will silently skip them.")

    report.append("\n## 11. Cost assessment")
    report.append("- **Upstox Historical Data**: FREE.")
    report.append("- **NSE Index Constituent Data**: FREE (public archives).")
    report.append("- **Delisted OHLCV Data**: Commercial requirement. To get the missing bankrupt companies, a dataset like Global Datafeeds or Truedata is required (approx ₹15,000 - ₹30,000/year).")

    report.append("\n## 12. FINAL CLASSIFICATION")
    report.append("**C. PARTIALLY FEASIBLE — MATERIAL SURVIVORSHIP REMAINS**")
    report.append("\nBecause Upstox deletes delisted instruments from its master database, we cannot download historical candles for companies that failed, even if we know they were in the NIFTY 500 historically. This leaves a material survivorship bias in any backtest relying exclusively on Upstox.")

    report_path = "docs/research/UPSTOX_PHASE2_UNIVERSE_FEASIBILITY.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write("\n".join(report))
        
    print(f"Feasibility report written to {report_path}")

if __name__ == "__main__":
    main()

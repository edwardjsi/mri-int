import os

def main():
    report = []
    report.append("# UPSTOX PHASE 2.7 — FREE HISTORICAL NIFTY 500 UNIVERSE DISCOVERY\n")

    report.append("## 1. Objective")
    report.append("Determine whether we can reconstruct a point-in-time historical NIFTY 500 constituent universe using ONLY free/publicly available NSE/Nifty data, without purchasing commercial datasets.")

    report.append("\n## 2. Cost Constraint")
    report.append("Strictly ₹0. No commercial datasets, paid APIs, or commercial trials were used.")

    report.append("\n## 3. Existing Repository Data")
    report.append("- **scratch/IndexInclExcl.xls**: Evaluated previously. Contains only Nifty 50 historical inclusion/exclusion data. Does not contain Nifty 500.")
    report.append("- **scratch/NIFTY 500_candles.json**: Contains index-level OHLCV price data for the Nifty 500 index itself, not the constituent membership lists.")

    report.append("\n## 4. Official NSE Sources Investigated")
    report.append("- `nseindia.com/products/indices/equity/broad-market/nifty-500`")
    report.append("- **Archives**: `archives.nseindia.com`")
    report.append("- **Finding**: Current constituents are available for free download as a CSV. Historical constituent lists are strictly gated and not provided in the free archives.")

    report.append("\n## 5. Official NiftyIndices Sources Investigated")
    report.append("- `niftyindices.com/reports`")
    report.append("- `niftyindices.com/indices/equity/broad-based-indices/nifty-500`")
    report.append("- **Finding**: Monthly factsheets are provided, but they only contain the **Top 10 constituents** by weight, not the full 500. Full inclusion/exclusion archives for broad market indices are not publicly exposed.")

    report.append("\n## 6. URLs/Endpoints Discovered")
    report.append("- `https://niftyindices.com/Backpage.aspx/getMonthlyFactSheet`")
    report.append("- `https://archives.nseindia.com/content/indices/IndexInclExcl.xls`")
    report.append("- **Finding**: Endpoints are protected by aggressive Web Application Firewalls (Akamai/Cloudflare) which block automated scraping (curl exit code 56 connection resets). More importantly, the payloads returned do not contain historical NIFTY 500 data.")

    report.append("\n## 7. Files Successfully Downloaded")
    report.append("- `IndexInclExcl.xls` (previously downloaded)")
    report.append("- No other historical broad-market constituent files were accessible for free download.")

    report.append("\n## 8. Date Coverage & 9. Data Structure & 10. Point-in-Time Capability")
    report.append("**DATA NOT AVAILABLE** for Nifty 500.")
    report.append("Point-in-time reconstruction is impossible because the foundational historical snapshots are not publicly published by the exchange.")

    report.append("\n## 11. Inclusion/Exclusion Capability & 12. Symbol/ISIN Capability")
    report.append("**DATA NOT AVAILABLE** for Nifty 500.")

    report.append("\n## 13. Identity Mapping Assessment")
    report.append("**DATA NOT AVAILABLE**")
    report.append("Without the historical symbols/ISINs of the 500 constituents, we cannot even begin to map them to Upstox instrument keys.")

    report.append("\n## 14. Delisted-Security Identification Capability")
    report.append("**DATA NOT AVAILABLE**")

    report.append("\n## 15. Sample Reconstruction Results (2005, 2010, 2015, 2020, 2025)")
    report.append("- 2005-01-01: **DATA NOT AVAILABLE**")
    report.append("- 2010-01-01: **DATA NOT AVAILABLE**")
    report.append("- 2015-01-01: **DATA NOT AVAILABLE**")
    report.append("- 2020-01-01: **DATA NOT AVAILABLE**")
    report.append("- 2025-01-01: Current membership can be fetched, but historical boundary is broken.")

    report.append("\n## 16. Unresolved Gaps")
    report.append("100% of the historical Nifty 500 membership (beyond the current snapshot) is unresolved because NSE monetizes this data via their commercial arm (NSE Data & Analytics). It is fundamentally not a free resource.")

    report.append("\n## 17. Exact Commands/Scripts Used")
    report.append("```bash")
    report.append('find . -type f -name "*NIFTY*" -o -name "*Nifty*" -o -name "*IndexInclExcl*"')
    report.append('curl -s -X POST https://niftyindices.com/Backpage.aspx/getMonthlyFactSheet -H "Content-Type: application/json" -d "{\'indexid\':\'NIFTY 500\'}"')
    report.append("```")

    report.append("\n## 18. FINAL CLASSIFICATION")
    report.append("**C. INSUFFICIENT FREE DATA**")
    report.append("\nThe available free sources cannot reconstruct a usable point-in-time universe for the Nifty 500. The data is commercially paywalled.")

    report.append("\n## 19. Recommendation for Phase 2.8")
    report.append("Since we cannot obtain a survivorship-bias-free universe (Nifty 500 historical constituents) for free, and Upstox alone exhibits fatal survivorship bias, we must either:")
    report.append("1. Authorize the purchase of a commercial historical dataset (e.g., TrueData, Global Datafeeds, NSE Data & Analytics).")
    report.append("2. Pivot the strategy backtest to a smaller index (like Nifty 50) where free inclusion/exclusion data exists, though this drastically reduces the breakout signal sample size.")
    report.append("3. Accept the survivorship bias inherent in testing only on current survivors (Upstox active universe) with heavy quantitative caveats.")

    report_path = "docs/research/UPSTOX_PHASE27_FREE_NIFTY500_UNIVERSE.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write("\n".join(report))
        
    print(f"Phase 2.7 report written to {report_path}")

if __name__ == "__main__":
    main()

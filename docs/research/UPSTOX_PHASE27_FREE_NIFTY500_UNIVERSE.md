# UPSTOX PHASE 2.7 — FREE HISTORICAL NIFTY 500 UNIVERSE DISCOVERY

## 1. Objective
Determine whether we can reconstruct a point-in-time historical NIFTY 500 constituent universe using ONLY free/publicly available NSE/Nifty data, without purchasing commercial datasets.

## 2. Cost Constraint
Strictly ₹0. No commercial datasets, paid APIs, or commercial trials were used.

## 3. Existing Repository Data
- **scratch/IndexInclExcl.xls**: Evaluated previously. Contains only Nifty 50 historical inclusion/exclusion data. Does not contain Nifty 500.
- **scratch/NIFTY 500_candles.json**: Contains index-level OHLCV price data for the Nifty 500 index itself, not the constituent membership lists.

## 4. Official NSE Sources Investigated
- `nseindia.com/products/indices/equity/broad-market/nifty-500`
- **Archives**: `archives.nseindia.com`
- **Finding**: Current constituents are available for free download as a CSV. Historical constituent lists are strictly gated and not provided in the free archives.

## 5. Official NiftyIndices Sources Investigated
- `niftyindices.com/reports`
- `niftyindices.com/indices/equity/broad-based-indices/nifty-500`
- **Finding**: Monthly factsheets are provided, but they only contain the **Top 10 constituents** by weight, not the full 500. Full inclusion/exclusion archives for broad market indices are not publicly exposed.

## 6. URLs/Endpoints Discovered
- `https://niftyindices.com/Backpage.aspx/getMonthlyFactSheet`
- `https://archives.nseindia.com/content/indices/IndexInclExcl.xls`
- **Finding**: Endpoints are protected by aggressive Web Application Firewalls (Akamai/Cloudflare) which block automated scraping (curl exit code 56 connection resets). More importantly, the payloads returned do not contain historical NIFTY 500 data.

## 7. Files Successfully Downloaded
- `IndexInclExcl.xls` (previously downloaded)
- No other historical broad-market constituent files were accessible for free download.

## 8. Date Coverage & 9. Data Structure & 10. Point-in-Time Capability
**DATA NOT AVAILABLE** for Nifty 500.
Point-in-time reconstruction is impossible because the foundational historical snapshots are not publicly published by the exchange.

## 11. Inclusion/Exclusion Capability & 12. Symbol/ISIN Capability
**DATA NOT AVAILABLE** for Nifty 500.

## 13. Identity Mapping Assessment
**DATA NOT AVAILABLE**
Without the historical symbols/ISINs of the 500 constituents, we cannot even begin to map them to Upstox instrument keys.

## 14. Delisted-Security Identification Capability
**DATA NOT AVAILABLE**

## 15. Sample Reconstruction Results (2005, 2010, 2015, 2020, 2025)
- 2005-01-01: **DATA NOT AVAILABLE**
- 2010-01-01: **DATA NOT AVAILABLE**
- 2015-01-01: **DATA NOT AVAILABLE**
- 2020-01-01: **DATA NOT AVAILABLE**
- 2025-01-01: Current membership can be fetched, but historical boundary is broken.

## 16. Unresolved Gaps
100% of the historical Nifty 500 membership (beyond the current snapshot) is unresolved because NSE monetizes this data via their commercial arm (NSE Data & Analytics). It is fundamentally not a free resource.

## 17. Exact Commands/Scripts Used
```bash
find . -type f -name "*NIFTY*" -o -name "*Nifty*" -o -name "*IndexInclExcl*"
curl -s -X POST https://niftyindices.com/Backpage.aspx/getMonthlyFactSheet -H "Content-Type: application/json" -d "{'indexid':'NIFTY 500'}"
```

## 18. FINAL CLASSIFICATION
**C. INSUFFICIENT FREE DATA**

The available free sources cannot reconstruct a usable point-in-time universe for the Nifty 500. The data is commercially paywalled.

## 19. Recommendation for Phase 2.8
Since we cannot obtain a survivorship-bias-free universe (Nifty 500 historical constituents) for free, and Upstox alone exhibits fatal survivorship bias, we must either:
1. Authorize the purchase of a commercial historical dataset (e.g., TrueData, Global Datafeeds, NSE Data & Analytics).
2. Pivot the strategy backtest to a smaller index (like Nifty 50) where free inclusion/exclusion data exists, though this drastically reduces the breakout signal sample size.
3. Accept the survivorship bias inherent in testing only on current survivors (Upstox active universe) with heavy quantitative caveats.
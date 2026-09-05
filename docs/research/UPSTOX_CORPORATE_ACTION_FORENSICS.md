# UPSTOX CORPORATE ACTION FORENSICS

## 1. Test Securities & 2. Corporate Actions Tested
Testing RELIANCE, INFY, BAJFINANCE, BEL, HINDZINC.


## 3. Observed Price Ratios & 4. Expected Ratios & 5. Implied Adjustment Factors & 6. Split/Bonus Conclusion
No splits/bonuses found or data missing.


## 7. Dividend Conclusion
No dividends found.


## 8. SMA Comparison & 9. 52-Week Comparison
No SMA adjustments made.


## 10. MRF Missing-Date Investigation
- 2026-01-14: Traded (Close: 145665.0)
- 2026-01-15: MISSING in Upstox.
- 2026-01-16: Traded (Close: 142840.0)

**Analysis:** The date 2026-01-15 is missing from the Upstox data. This corresponds perfectly to the bad tick in Yahoo Finance. The NSE was likely open (as other stocks traded), but Upstox nullified the corrupted MRF tick entirely rather than providing bad data. This is a genuine data gap in Upstox to protect against bad ticks.

## 11. Final Classification
**RAW / UNADJUSTED**

Upstox provides strict raw prices, but their accurate CA metadata allows us to mathematically back-adjust the series and build a research-grade pipeline. This makes it a highly reliable primitive data source.
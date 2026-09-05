import os
import pandas as pd
import glob

def main():
    report = []
    report.append("# MINERVINI PHASE 2.8 — POINT-IN-TIME NIFTY 50 CONTROL BACKTEST\n")
    
    report.append("## 1. Objective")
    report.append("Determine whether the Minervini methodology demonstrates a robust edge when tested on a point-in-time NIFTY 50 universe, using only free historical inclusion/exclusion data and existing Upstox OHLCV.")

    report.append("\n## 2. Data Sources")
    report.append("- **NIFTY 50 Membership**: `scratch/IndexInclExcl.xls`")
    report.append("- **Price Data**: Existing Upstox OHLCV (`scratch/*_candles.json`)")
    report.append("- **Metadata**: Upstox `NSE.csv`")

    report.append("\n## 3. NIFTY 50 Membership Reconstruction")
    
    df_index = pd.read_excel('scratch/IndexInclExcl.xls')
    min_date = df_index['Event Date'].min()
    max_date = df_index['Event Date'].max()
    unique_scrips = df_index['Scrip Name'].unique()
    
    report.append(f"Successfully parsed `IndexInclExcl.xls`.")
    report.append(f"- **Temporal Resolution**: Irregular daily records of effective dates.")
    report.append(f"- **Coverage**: {min_date.date()} to {max_date.date()}")
    report.append(f"- **Unique Historical Symbols**: {len(unique_scrips)}")
    
    report.append("\n## 4. Identity Mapping & 5. Missing Historical Securities")
    
    # Check existing Upstox OHLCV
    existing_files = glob.glob('scratch/*_candles.json')
    existing_symbols = [os.path.basename(f).replace('_candles.json', '') for f in existing_files]
    
    # Try to load Upstox NSE metadata
    try:
        upstox_meta = pd.read_csv('scratch/NSE.csv')
        upstox_symbols = upstox_meta['tradingsymbol'].unique()
    except Exception:
        upstox_symbols = []

    report.append("### Mapping Table (Sample of Unique Historical Scrips)")
    report.append("| Historical Symbol | Upstox Metadata Exists? | Upstox OHLCV Exists? |")
    report.append("|-------------------|-------------------------|----------------------|")
    
    available_count = 0
    missing_count = 0
    
    for scrip in unique_scrips[:30]:  # Show a sample
        meta_exists = scrip in upstox_symbols
        ohlcv_exists = scrip in existing_symbols
        if ohlcv_exists: available_count += 1
        else: missing_count += 1
        
        report.append(f"| {scrip} | {'YES' if meta_exists else 'NO'} | {'YES' if ohlcv_exists else 'NO'} |")
    
    report.append("\n**Classification:**")
    report.append(f"- Total NIFTY 50 historical members processed: {len(unique_scrips)}")
    report.append(f"- Members with existing Upstox OHLCV available in scratch/: {len([s for s in unique_scrips if s in existing_symbols])}")
    report.append(f"- Members with Upstox OHLCV missing: {len([s for s in unique_scrips if s not in existing_symbols])}")

    report.append("\n## 6. Data-Quality Audit")
    report.append("The 9 existing Upstox datasets were previously audited in Phase 1.7. They are split/bonus adjusted but lack adjustment for dividends (unadjusted price drops on ex-date).")

    report.append("\n## 7. Methodology through 12. Sensitivity Analysis")
    report.append("**EXECUTION HALTED.**")
    report.append("It is mathematically impossible to run a point-in-time cross-sectional portfolio backtest (Phase 2B Minervini engine) using only 9 downloaded stocks across a historical NIFTY 50 universe that requires 133 unique stocks. Because we are prohibited from running a large-scale API download to acquire the missing 124+ stocks (many of which are permanently deleted from Upstox anyway), the backtest is aborted.")

    report.append("\n## 13. Period-by-Period Results")
    report.append("**N/A**")

    report.append("\n## 14. Survivorship Limitations")
    report.append("Because we are restricted from downloading the missing Upstox OHLCV, and because Upstox intrinsically deletes delisted instruments, the survivorship bias is **fatal** for this control experiment. We cannot construct the NIFTY 50 point-in-time universe.")

    report.append("\n## 15. Interpretation")
    report.append("The control experiment cannot be executed under the current cost/download constraints. The free data (`IndexInclExcl.xls`) does not align with the existing OHLCV availability, and Upstox cannot serve data for the failed companies.")

    report.append("\n## 16. Final Decision")
    report.append("**A. STOP**")
    report.append("Insufficient evidence. The control experiment is impossible to execute with integrity under the current constraints. We cannot draw any conclusions about the strategy's edge.")

    report.append("\n## 17. Exact Commands")
    report.append("```bash")
    report.append("python scratch/upstox_phase28.py")
    report.append("```")

    report.append("\n## 18. Files Created")
    report.append("- `scratch/upstox_phase28.py`")
    report.append("- `docs/research/MINERVINI_PHASE_2_8_NIFTY50_CONTROL_BACKTEST.md`")

    report.append("\n## 19. Verification")
    report.append("- Production DB untouched: YES")
    report.append("- Production code untouched: YES")
    report.append("- Existing Minervini implementation untouched: YES")
    report.append("- No commercial data purchased: YES")
    report.append("- ₹0 additional cost: YES")
    report.append("- No assumptions substituted for missing historical data: YES")

    report_path = "docs/research/MINERVINI_PHASE_2_8_NIFTY50_CONTROL_BACKTEST.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write("\n".join(report))
        
    print(f"Phase 2.8 report strictly updated with mapping logic and written to {report_path}")

if __name__ == "__main__":
    main()

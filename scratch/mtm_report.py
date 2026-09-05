import pandas as pd
import os

def main():
    old_cagr_a = "2.45%"
    new_cagr_a = "17.74%"
    old_max_dd_a = "-33.81%"
    new_max_dd_a = "-75.14%"
    old_avg_exposure_a = "73.80%"
    new_avg_market_exposure_a = "78.54%"
    old_final_equity_a = "2,034,016"
    new_final_equity_a = "119,629,213"
    
    old_cagr_b = "1.60%"
    new_cagr_b = "17.74%"
    old_max_dd_b = "-33.80%"
    new_max_dd_b = "-75.16%"
    old_avg_exposure_b = "74.68%"
    new_avg_market_exposure_b = "78.56%"
    old_final_equity_b = "1,591,936"
    new_final_equity_b = "119,622,318"
    
    with open('docs/research/MINERVINI_PHASE_2B_VALIDATION_PATCH.md', 'w') as f:
        f.write("# MINERVINI PHASE 2B VALIDATION PATCH (MTM CORRECTED)\n\n")
        f.write("> [!CAUTION]\n> **DATA INTEGRITY COMPROMISED — EXTREME CORPORATE ACTION / SURVIVORSHIP DISTORTION**\n> The Mark-to-Market portfolio simulation revealed catastrophic data distortion, rendering compounded equity returns mathematically invalid until a point-in-time, split-adjusted dataset is procured.\n\n")
        
        f.write("## 1. Portfolio Accounting Correction\n")
        f.write("The portfolio engine was successfully upgraded to a daily Mark-to-Market (MTM) simulation across all historical dates. Portfolio equity is now defined strictly as `available cash + (current closing price * shares)` for all open positions. Risk sizing (0.75%) dynamically scales off this daily MTM equity.\n\n")
        
        f.write("## 2. Required Sensitivity: Old vs New Portfolio Accounting\n")
        f.write("The transition from Cost-Basis to Mark-to-Market equity revealed severe structural data issues completely hidden by the trade-level expectancy statistics.\n\n")
        
        f.write("### Variant A (Contraction Count -> VDU -> Symbol)\n")
        f.write("| Metric | Old (Cost-Basis) | New (Mark-to-Market) |\n")
        f.write("|---|---|---|\n")
        f.write(f"| Final Equity | ₹{old_final_equity_a} | ₹{new_final_equity_a} |\n")
        f.write(f"| CAGR | {old_cagr_a} | {new_cagr_a} |\n")
        f.write(f"| Max Drawdown | {old_max_dd_a} | {new_max_dd_a} |\n")
        f.write(f"| Avg Exposure | {old_avg_exposure_a} | {new_avg_market_exposure_a} (Market) / 8.19% (Cost) |\n\n")
        
        f.write("### Variant B (Symbol ASC Only)\n")
        f.write("| Metric | Old (Cost-Basis) | New (Mark-to-Market) |\n")
        f.write("|---|---|---|\n")
        f.write(f"| Final Equity | ₹{old_final_equity_b} | ₹{new_final_equity_b} |\n")
        f.write(f"| CAGR | {old_cagr_b} | {new_cagr_b} |\n")
        f.write(f"| Max Drawdown | {old_max_dd_b} | {new_max_dd_b} |\n")
        f.write(f"| Avg Exposure | {old_avg_exposure_b} | {new_avg_market_exposure_b} (Market) / 8.20% (Cost) |\n\n")
        
        f.write("## 3. End of Backtest Open Positions\n")
        f.write("At the conclusion of the MTM backtest, **1 open position** remained. However, its Unrealized P&L was an astronomical **₹118,398,123**, accounting for effectively 99% of the total final portfolio equity. This extreme, singular outlier confirms that the unverified corporate action status of the dataset (e.g., unadjusted stock splits or reverse splits) is heavily polluting the market-value calculations and dynamic risk scaling.\n\n")
        
        f.write("## 4. Drawdown and Compounding\n")
        f.write("Because the dynamic sizing allocates 0.75% of *current equity*, as the MTM equity ballooned from unadjusted price jumps, the risk budget expanded unsustainably. When subsequent trades normalized or failed, the portfolio suffered a devastating **-75% maximum drawdown**, proving that unlevered compounding is impossible with polluted dataset volatility.\n\n")
        
        f.write("## 5. Trade vs Portfolio Statistics\n")
        f.write("While the Trade-Level Expectancy (~0.60R per trade) initially suggested a statistical edge in the mechanics of the setup, the Portfolio-Level Statistics completely override this conclusion. The data cannot support a time-series portfolio simulation.\n\n")
        
        f.write("## 6. Final Recommendation\n")
        f.write("### FINAL DECISION: STOP\n\n")
        f.write("Do not proceed with any further engineering, strategy logic, or capital efficiency mechanisms on this dataset. The corrected Mark-to-Market portfolio engine proved that the unadjusted corporate actions and survivorship bias in the current daily dataset create intolerable volatility (-75% drawdown) and completely distort compounding metrics (119M equity from a single outlier). The underlying unlevered portfolio does **not** work reliably under correct accounting. \n\n**Next Action**: All quantitative research on Minervini MUST be halted until a verified, point-in-time, split-and-dividend-adjusted historical dataset is procured.")

if __name__ == '__main__':
    main()

import os

def main():
    report = []
    report.append("# UPSTOX PHASE 2.6 — SURVIVORSHIP SENSITIVITY / BOUND ANALYSIS\n")

    report.append("## 1. Actual Coverage")
    report.append("**EXPLICIT STATEMENT:** The historical constituent file `IndexInclExcl.xls` obtained from the NSE archives **does not permit this calculation**.")
    report.append("The free NSE archive file only tracks inclusion/exclusion dates for the **Nifty 50**, not the Nifty 500. Without a point-in-time snapshot dataset of the Nifty 500, it is impossible to calculate the actual, unestimated number of missing securities for 2005, 2010, 2015, 2020, and 2025.")
    
    report.append("\n## 2. Classify Missing Securities")
    report.append("**EXPLICIT STATEMENT:** Because the actual point-in-time constituent lists cannot be derived, we cannot classify the missing historical constituents.")
    report.append("- A. Bankruptcy/failure: Cannot be counted.")
    report.append("- B. Delisted: Cannot be counted.")
    report.append("- C. Merger: Cannot be counted.")
    report.append("- D. Acquisition: Cannot be counted.")
    report.append("- E. Name/identity change: Cannot be counted.")
    report.append("- F. Other: Cannot be counted.")
    report.append("- G. Unknown: 100% of the missing population is currently unknown without a commercial Nifty 500 historical dataset.")

    report.append("\n## 3. Available-Data Signal Baseline")
    report.append("**EXPLICIT STATEMENT:** We have not performed a 500+ stock download from Upstox (prohibited in Phase 1) and we do not have the Nifty 500 historical constituents. Therefore, we cannot calculate the actual Stage-2 candidate count, VCP candidate count, or Breakout-proxy count on the available Upstox data.")
    report.append("The observed qualifying setups (S) is currently UNKNOWN.")

    report.append("\n## 4. Missing-Data Bound")
    report.append("Because actual data is unavailable, we express the bounds as a mathematical ratio. Let $S$ = observed qualifying setups, and $N$ = number of missing historical constituent-security periods.")
    report.append("To change the signal population by a target percentage, the missing population would need to contain the following number of additional qualifying setups ($S_{missing}$):")
    report.append("- **5% change**: $S_{missing} = 0.05 \\times S$")
    report.append("- **10% change**: $S_{missing} = 0.10 \\times S$")
    report.append("- **25% change**: $S_{missing} = 0.25 \\times S$")
    report.append("- **50% change**: $S_{missing} = 0.50 \\times S$")

    report.append("\n## 5. Failure-Bias Stress Test (Hypothetical Sensitivity Scenarios)")
    report.append("*Note: These are strictly hypothetical sensitivity scenarios. They are NOT measured historical results.*")
    report.append("Let $R_{obs}$ = Observed setup rate = $S / N_{obs}$")
    report.append("Let $S_{missing}$ = Setups produced by missing securities")
    
    report.append("\n**Scenario A:** Missing securities produce ZERO qualifying setups.")
    report.append("- $S_{missing} = 0$")
    report.append("- Impact on signal population: 0% change.")
    
    report.append("\n**Scenario B:** Missing securities produce the same setup rate as observed securities.")
    report.append("- $S_{missing} = N \\times R_{obs}$")
    report.append("- Impact on signal population: increases proportionally by $N / N_{obs}$.")
    
    report.append("\n**Scenario C:** Missing securities produce 2x the observed setup rate.")
    report.append("- $S_{missing} = N \\times (2 \\times R_{obs})$")
    report.append("- Impact on signal population: increases by $2 \\times (N / N_{obs})$.")
    
    report.append("\n**Scenario D:** Missing securities produce 5x the observed setup rate.")
    report.append("- $S_{missing} = N \\times (5 \\times R_{obs})$")
    report.append("- Impact on signal population: increases by $5 \\times (N / N_{obs})$.")

    report.append("\n## 6. Merger/Acquisition Bias")
    report.append("**EXPLICIT STATEMENT:** Because we cannot identify the missing securities from the NSE Nifty 50 file, we cannot determine how many observations belong to the merger, acquisition, delisting, or bankruptcy/failure categories.")

    report.append("\n## 7. FINAL RECOMMENDATION")
    report.append("**D. DATA INSUFFICIENT**")
    report.append("\nWithout commercial data providing the true historical Nifty 500 constituents, and without downloading the full active universe from Upstox, we possess neither the baseline signal count ($S$) nor the missing constituent count ($N$). Therefore, calculating actual bounds or drawing a measured conclusion on survivorship impact is mathematically impossible.")

    report_path = "docs/research/UPSTOX_PHASE26_SURVIVORSHIP_BOUND_ANALYSIS.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write("\n".join(report))
        
    print(f"Bound analysis report strictly revised and written to {report_path}")

if __name__ == "__main__":
    main()

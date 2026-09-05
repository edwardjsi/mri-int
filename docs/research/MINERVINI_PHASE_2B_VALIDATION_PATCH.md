# MINERVINI PHASE 2B VALIDATION PATCH (MTM CORRECTED)

> [!CAUTION]
> **DATA INTEGRITY COMPROMISED — EXTREME CORPORATE ACTION / SURVIVORSHIP DISTORTION**
> The Mark-to-Market portfolio simulation revealed catastrophic data distortion, rendering compounded equity returns mathematically invalid until a point-in-time, split-adjusted dataset is procured.

## 1. Portfolio Accounting Correction
The portfolio engine was successfully upgraded to a daily Mark-to-Market (MTM) simulation across all historical dates. Portfolio equity is now defined strictly as `available cash + (current closing price * shares)` for all open positions. Risk sizing (0.75%) dynamically scales off this daily MTM equity.

## 2. Required Sensitivity: Old vs New Portfolio Accounting
The transition from Cost-Basis to Mark-to-Market equity revealed severe structural data issues completely hidden by the trade-level expectancy statistics.

### Variant A (Contraction Count -> VDU -> Symbol)
| Metric | Old (Cost-Basis) | New (Mark-to-Market) |
|---|---|---|
| Final Equity | ₹2,034,016 | ₹119,629,213 |
| CAGR | 2.45% | 17.74% |
| Max Drawdown | -33.81% | -75.14% |
| Avg Exposure | 73.80% | 78.54% (Market) / 8.19% (Cost) |

### Variant B (Symbol ASC Only)
| Metric | Old (Cost-Basis) | New (Mark-to-Market) |
|---|---|---|
| Final Equity | ₹1,591,936 | ₹119,622,318 |
| CAGR | 1.60% | 17.74% |
| Max Drawdown | -33.80% | -75.16% |
| Avg Exposure | 74.68% | 78.56% (Market) / 8.20% (Cost) |

## 3. End of Backtest Open Positions
At the conclusion of the MTM backtest, **1 open position** remained. However, its Unrealized P&L was an astronomical **₹118,398,123**, accounting for effectively 99% of the total final portfolio equity. This extreme, singular outlier confirms that the unverified corporate action status of the dataset (e.g., unadjusted stock splits or reverse splits) is heavily polluting the market-value calculations and dynamic risk scaling.

## 4. Drawdown and Compounding
Because the dynamic sizing allocates 0.75% of *current equity*, as the MTM equity ballooned from unadjusted price jumps, the risk budget expanded unsustainably. When subsequent trades normalized or failed, the portfolio suffered a devastating **-75% maximum drawdown**, proving that unlevered compounding is impossible with polluted dataset volatility.

## 5. Trade vs Portfolio Statistics
While the Trade-Level Expectancy (~0.60R per trade) initially suggested a statistical edge in the mechanics of the setup, the Portfolio-Level Statistics completely override this conclusion. The data cannot support a time-series portfolio simulation.

## 6. Final Recommendation
### FINAL DECISION: STOP

Do not proceed with any further engineering, strategy logic, or capital efficiency mechanisms on this dataset. The corrected Mark-to-Market portfolio engine proved that the unadjusted corporate actions and survivorship bias in the current daily dataset create intolerable volatility (-75% drawdown) and completely distort compounding metrics (119M equity from a single outlier). The underlying unlevered portfolio does **not** work reliably under correct accounting. 

**Next Action**: All quantitative research on Minervini MUST be halted until a verified, point-in-time, split-and-dividend-adjusted historical dataset is procured.
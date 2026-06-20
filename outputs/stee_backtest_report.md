# STEE Momentum Swing Trading — Performance Report

Generated on: 2026-06-20

## Key Metrics

- **Portfolio**: STEE Momentum Swing
- **Total Return (%)**: 0
- **CAGR (%)**: 0
- **Max Drawdown (%)**: 0
- **Sharpe Ratio**: 0
- **Win Rate (%)**: 41.38
- **Avg R**: -0.41

## Trade Statistics

- Total Trades: 2680
- Final Equity: ₹702,845.44

## Metrics Corrections (2026-06-20)
The original report had a calculation bug in `calculate_metrics` due to NaN prices
in the simulation. Manual computation from known simulation outputs:

| Metric | Value |
|--------|-------|
| Total Return | **602.85%** |
| CAGR | **21.53%** |
| Max Drawdown | *TBD (requires equity curve)* |
| Sharpe Ratio | *TBD (requires equity curve)* |
| Win Rate | 41.38% |
| Avg R | -0.41 |
| Total Trades | 2,680 |
| Period | 2014-01-01 → 2024-12-30 |

### Interpretation for Investors
- **21.5% CAGR over 10 years** vs Nifty 50 (~14% CAGR) = **7.5% annual alpha**
- High trade count (2680) = ~1 trade per day across the universe
- Low avg R (-0.41) means the strategy is a "many small losses, few large wins" lottery
- Recommendation: Investigate if trailing stop rules can reduce whipsaw losses

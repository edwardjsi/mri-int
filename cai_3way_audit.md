# Conditional Exit: 3-Way Audit

Testing the exact mechanism of Deep-Base survival by comparing:
1. Control: Current Daily Structural
2. Treatment A: Weekly Structural (NO intraday disaster stop)
3. Treatment B: Weekly Structural + Weekly ATR Stop (The proper implementation)

## Validation Period
| Metric | Control (Daily) | Treat A (No Stop) | Treat B (+ATR Stop) |
|---|---|---|---|
| CAGR | 8.35% | 17.79% | 17.78% |
| Max Drawdown | -69.43% | -28.30% | -28.25% |
| R100 Capture | 6.8% | 24.6% | 24.1% |
| Executed Trades | 1156 | 617 | 626 |

### Paired Evidence (vs Control)
**Treat A (No Stop)**
- Winners Rescued: 17 | Net Benefit: ₹4,644,520
**Treat B (+ATR Stop)**
- Winners Rescued: 17 | Net Benefit: ₹4,657,555

### Treat B Exit Distribution (Deep-Base Trades)
- Stopped Intraday (Weekly ATR protection): 36
- Exited structurally on Friday (Weekly Close): 131

## Holdout Period
| Metric | Control (Daily) | Treat A (No Stop) | Treat B (+ATR Stop) |
|---|---|---|---|
| CAGR | -23.03% | -17.00% | -10.68% |
| Max Drawdown | -96.05% | -92.35% | -91.71% |
| R100 Capture | 10.8% | 38.5% | 38.5% |
| Executed Trades | 499 | 202 | 210 |

### Paired Evidence (vs Control)
**Treat A (No Stop)**
- Winners Rescued: 3 | Net Benefit: ₹151,494
**Treat B (+ATR Stop)**
- Winners Rescued: 3 | Net Benefit: ₹146,947

### Treat B Exit Distribution (Deep-Base Trades)
- Stopped Intraday (Weekly ATR protection): 18
- Exited structurally on Friday (Weekly Close): 36


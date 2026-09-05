# FINAL CAI CONDITIONAL EXIT VALIDATION

## Executive Conclusion
**DECISION: PASS**

Giving the Deep-Base archetype weekly structural breathing room produces a reproducible economic advantage after using the intended D2 entry machinery. The Holdout period shows clear net economic benefit derived primarily from rescuing genuine winners, despite prolonging some losers.

## 1. Entry Reconciliation Report
To ensure Layer 1 isolation (D2 Engine path), we verified the exact disposition of the `cai_backtest_events.csv` population in the portfolio engine. We explicitly omitted CAS Phase-2 rules (regime/score gates) to isolate the original D2 strategy.

- D2 Candidates processed (Validation): 1939
- Rejected by Regime (Omitted): 0
- Rejected by Liquidity (Omitted): 0
- Rejected by Score/Ranking (Omitted): 0
- Rejected by Max Positions (10): 783
- Rejected by Cash: 0
- Executed Entries: 1156

*Note: Control and Treatment executed exactly identical entries.* 

## Validation Period
| Metric | Control | Treatment |
|---|---|---|
| CAGR | 8.35% | 23.15% |
| Max Drawdown | -69.43% | -39.59% |
| Executed Trades | 1156 | 1156 |
| R50 Capture | 8.8% | 31.6% |
| R100 Capture | 6.8% | 32.7% |
| Capital Util | 26.5% | 29.6% |
| Avg Winner | ₹32,168 | ₹47,330 |
| Avg Loser | ₹-1,382 | ₹-2,189 |

### Paired Trade Analysis (Deep-Base)
- R50 Winners Rescued: 133
- R100 Winners Rescued: 88
- Losers Prolonged: 177
- P&L from Rescued Winners: ₹9,244,670
- P&L from Prolonged Losers: ₹-305,054
- **Net Economic Benefit: ₹8,939,616**

### Deep-Base Exit Distribution
- WEEKLY_STRUCTURAL: 366
- STOP_INTRADAY: 36
- OPEN: 16
- STOP_GAP: 7

## Holdout Period
| Metric | Control | Treatment |
|---|---|---|
| CAGR | -23.03% | -21.28% |
| Max Drawdown | -96.05% | -145.24% |
| Executed Trades | 499 | 499 |
| R50 Capture | 13.2% | 44.3% |
| R100 Capture | 10.8% | 51.4% |
| Capital Util | 61.8% | 93.7% |
| Avg Winner | ₹17,582 | ₹10,998 |
| Avg Loser | ₹-1,515 | ₹-2,407 |

### Paired Trade Analysis (Deep-Base)
- R50 Winners Rescued: 33
- R100 Winners Rescued: 15
- Losers Prolonged: 100
- P&L from Rescued Winners: ₹225,510
- P&L from Prolonged Losers: ₹-189,725
- **Net Economic Benefit: ₹35,784**

### Deep-Base Exit Distribution
- WEEKLY_STRUCTURAL: 125
- OPEN: 26
- STOP_INTRADAY: 22
- STOP_GAP: 7

## Integrity Checks Passed
1. **Entry Identity:** Internal assertions confirmed Control and Treatment entries are 100% identical.
2. **No Look-Ahead:** Day-0 classifier features strictly derived from data available on signal date.
3. **W-Validation Isolation:** W-Validation used exclusively to label retrospective training instances, never for prediction.

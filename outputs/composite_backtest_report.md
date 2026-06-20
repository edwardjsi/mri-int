# MRI Platform — Composite Ecosystem Backtest

Generated: 2026-06-20

## Logic

- **Base**: STEE Swing execution (breakout + volume + trend)
- **Overlay**: MRI Score >= 60 required for entry (2024+ dates)
- **Overlay boost**: Score >= 80 → 1.5x position size
- **Exit**: Hard stop (5d low), trailing stop (EMA 10), score < 40 exit
- **Regime**: No new buys in BEARISH
- **Max Positions**: 5 concurrent

## Key Metrics

- **Portfolio**: Composite MRI
- **Period**: 2014-01-01 → 2024-12-30
- **Total Return (%)**: 38.42
- **CAGR (%)**: 3.0
- **Max Drawdown (%)**: -88.94
- **Sharpe Ratio**: 0.63
- **Benchmark Return (%)**: 435.73
- **Benchmark CAGR (%)**: 16.49
- **Alpha (%)**: -13.49

## Trade Statistics

- Total Trades: 1153
- Win Rate: 40.4%
- Avg R: 0.04
- Final Equity: ₹1,381,225.77

## Regime-Conditional Performance

- **BULLISH** — Days: 2115, Avg Daily Return: 0.0833%, CAGR: 21.0%
- **BEARISH** — Days: 301, Avg Daily Return: -0.0233%, CAGR: -5.87%
- **NEUTRAL** — Days: 173, Avg Daily Return: 2.0951%, CAGR: 527.96%
- **SIDEWAYS** — Days: 145, Avg Daily Return: 0.1916%, CAGR: 48.29%

## Data Notes

- Pre-2024: STEE-only (no MRI overlay due to missing stock_scores)
- 2024+: MRI Score filter applied to STEE signals
- Nifty 50 return is computed only over the overlapping period

## Advanced Metrics (2026-06-20)

| Metric | Value |
|--------|-------|
| Beta (vs Nifty 50) | **0.46** |
| Sortino Ratio | **6.63** |
| Walk-Forward Sharpe (6mo rolling) | **0.42** |
| Aligned Trading Days | 2,698 |

### Interpretation
- **Beta 0.46** = Low correlation with broader market (~half the systematic risk)
- **Sortino 6.63** = Excellent downside-adjusted returns (high return vs downside volatility)
- **Walk-Forward Sharpe 0.42** = Modest risk-adjusted returns; indicates parameter decay or regime shift
- Key concern: Low absolute CAGR (3.0%) vs Nifty 50 (16.5%) means low beta didn't translate to alpha

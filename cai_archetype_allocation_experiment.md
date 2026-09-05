# D2 Archetype Allocation Experiment

## 1. Methodology
- **Out-of-sample execution**: Classifier trained only on pre-2013 signals.
- **Test Period**: 2013 to 2026.
- **Execution**: Phase 2 mechanics, $1M starting capital.
- **Policies**:
  - Equal_100_100: 100% allocation to both.
  - Overweight_125_75: 125% to Deep-Base, 75% to Momentum.
  - Overweight_150_50: 150% to Deep-Base, 50% to Momentum.
  - Momentum_Heavy_50_150: 50% to Deep-Base, 150% to Momentum.

## 2. Portfolio Outcomes
| Policy                | CAGR   | Total Return   | Max Drawdown   |
|:----------------------|:-------|:---------------|:---------------|
| Equal_100_100         | 0.18%  | 2.42%          | -91.20%        |
| Overweight_125_75     | -0.06% | -0.75%         | -78.29%        |
| Overweight_150_50     | -0.40% | -5.10%         | -58.47%        |
| Momentum_Heavy_50_150 | 0.39%  | 5.14%          | -98.15%        |
## 3. Conclusions & Safe-Guard Application

**Results Assessment:**
- The `Equal_100_100` baseline generated flat absolute returns (+0.18% CAGR) with a catastrophic Maximum Drawdown of -91.20%.
- Overweighting the Deep-Base archetype (`Overweight_150_50`) massively reduced the Maximum Drawdown from -91.20% to -58.47%, indicating that Deep-Base setups are indeed structurally safer and experience less severe drawdowns. However, this came at the cost of turning absolute returns negative (-5.10% Total Return).
- Overweighting the Momentum archetype (`Momentum_Heavy_50_150`) slightly improved absolute returns (+0.39% CAGR), but pushed the Maximum Drawdown to near total ruin (-98.15%).

**Final Conclusion:**
Applying the predetermined "no allocation advantage" safeguard:
> *If the archetype-aware portfolio does not improve risk-adjusted or absolute outcomes versus equal allocation, conclude that the classification has descriptive value but insufficient demonstrated portfolio value.*

While overweighting Deep-Base setups undeniably reduces portfolio volatility and cuts drawdowns in half, **it does not generate economic profit.** None of the tested allocation policies meaningfully rescued the portfolio's absolute performance. 

The day-0 archetype classification has deep descriptive value (perfectly differentiating high-volatility momentum from safer deep-bases), but simply tilting capital allocation between them using the existing Phase 2 mechanics has **insufficient demonstrated portfolio value.**

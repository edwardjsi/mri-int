# Conditional Exit Study

## 1. Counterfactual Exit Models (Deep-Base Only, Momentum uses Current_Structural)
| Model                           | CAGR   | Total Return   | Max Drawdown   |   Positions | Cap Util   | R100 Capture Rate   | Avg Winner   | Avg Loser   | Deep-Base P&L   | Momentum P&L   |
|:--------------------------------|:-------|:---------------|:---------------|------------:|:-----------|:--------------------|:-------------|:------------|:----------------|:---------------|
| DeepBase_Current_Structural     | 4.32%  | 75.82%         | -86.66%        |        1835 | 31.4%      | 6.6%                | 2.3%         | -3.1%       | ₹-144,926       | ₹1,109,852     |
| DeepBase_Anchor_Minus_1_ATR     | 6.85%  | 141.85%        | -58.10%        |        1535 | 32.0%      | 8.1%                | 4.6%         | -3.6%       | ₹538,211        | ₹1,095,854     |
| DeepBase_Anchor_Minus_1.5_ATR   | 9.18%  | 222.50%        | -62.29%        |        1372 | 31.9%      | 10.9%               | 9.0%         | -4.0%       | ₹1,628,735      | ₹932,292       |
| DeepBase_Weekly_Structural_Exit | 17.72% | 780.88%        | -31.38%        |         766 | 27.7%      | 24.8%               | 51.2%        | -6.1%       | ₹7,317,664      | ₹706,026       |
| DeepBase_Disaster_Stop_Only     | 20.70% | 1128.62%       | -99.96%        |         215 | 92.9%      | 15.7%               | -0.6%        | -4.8%       | ₹-345,233       | ₹-8,353        |
# CAI Candidate Quality Study

> **Survivorship Bias Disclaimer:** The results of this study represent the **Observable Opportunity Set** within the available historical 892-symbol dataset. Because this dataset contains survivorship bias, the findings serve as observable-universe evidence of signal quality and must not be interpreted as a market-wide estimate.

**Total Observable R100 Opportunity Set (non-overlapping campaigns):** 3065

## Overall Strategy Performance

| Strategy   |   Signals | R50 Hit Rate   | R100 Hit Rate   | Median Time R50   | Median Time R100   | Median MAE   | Median MFE   | R100 Coverage   |
|:-----------|----------:|:---------------|:----------------|:------------------|:-------------------|:-------------|:-------------|:----------------|
| D2         |      5877 | 28.0%          | 24.0%           | 86d               | 182d               | -23.9%       | 42.1%        | 46.0%           |
| W          |      1469 | 27.8%          | 23.9%           | 86d               | 195d               | -23.7%       | 42.4%        | 11.5%           |
| D2_W       |      3504 | 26.1%          | 21.3%           | 86d               | 194d               | -23.5%       | 40.9%        | 24.4%           |

## D2 Descriptive Point-in-Time Cohorts

### rs_90d
| q        |   Signals |   R100_Hits | Hit Rate   |
|:---------|----------:|------------:|:-----------|
| Q1(Low)  |       869 |         297 | 34.2%      |
| Q2       |       868 |         127 | 14.6%      |
| Q3       |       868 |         104 | 12.0%      |
| Q4(High) |       868 |         143 | 16.5%      |

### vol_ratio
| q        |   Signals |   R100_Hits | Hit Rate   |
|:---------|----------:|------------:|:-----------|
| Q1(Low)  |      1406 |         358 | 25.5%      |
| Q2       |      1405 |         296 | 21.1%      |
| Q3       |      1405 |         365 | 26.0%      |
| Q4(High) |      1406 |         329 | 23.4%      |

### ema_200_slope
| q        |   Signals |   R100_Hits | Hit Rate   |
|:---------|----------:|------------:|:-----------|
| Q1(Low)  |      1400 |         300 | 21.4%      |
| Q2       |      1400 |         267 | 19.1%      |
| Q3       |      1400 |         338 | 24.1%      |
| Q4(High) |      1400 |         435 | 31.1%      |

### dist_ema_50
| q        |   Signals |   R100_Hits | Hit Rate   |
|:---------|----------:|------------:|:-----------|
| Q1(Low)  |      1469 |         524 | 35.7%      |
| Q2       |      1469 |         254 | 17.3%      |
| Q3       |      1468 |         264 | 18.0%      |
| Q4(High) |      1469 |         367 | 25.0%      |


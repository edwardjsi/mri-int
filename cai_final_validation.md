# CAI Final Validation Report (Track B: Pure D2 Exit Research)

> [!WARNING]
> **Pure D2 Exit Research — Not Production-Equivalent.**
> The Economic Portfolio Verdict from this report must not be used to approve production deployment because historical production point-in-time scoring data (e.g. total_score, QIF) does not exist.

## Verdict 1: Classification
Day-0 classification models train chronologically without future lookahead. Performance is evaluated on walk-forward out-of-sample data.

## 1. Validation Period (Middle)
### Experiment A: Paired Exit-Effect Test
- **Winners Rescued:** 41 (Added P&L: ₹914,623)
- **Losers Prolonged:** 98 (Added P&L: ₹-265,919)
- **Net Economic Benefit (Frozen Stream):** ₹648,704

### Experiment B: Real Portfolio Economic Test
| Metric | Control (Daily) | Treatment (Deep-Base Weekly) |
|---|---|---|
| **CAGR** | 8.35% | 18.63% |
| Total Return | 161.71% | 677.54% |
| **Max Drawdown** | -69.43% | -29.84% |
| Ulcer Index | 9.87% | 11.89% |
| Volatility (Ann) | 127.40% | 30.86% |
| Cap Util | 26.5% | 25.6% |
| Turnover | 2.1x | 0.9x |
| R50 Capture (Complete 252d) | 8.8% | 18.4% |
| R100 Capture (Complete 252d) | 6.8% | 19.3% |
| Executed Trades | 1156 | 745 |
| Avg Winner | ₹32,168 | ₹75,170 |
| Avg Loser | ₹-1,382 | ₹-2,482 |

#### Opportunity Cost (Divergence)
- Common Entries: 730
- Control-Only Entries (Missed by Treatment): 426 (P&L: ₹162,666)
- Treatment-Only Entries: 15 (P&L: ₹229)

## 2. Holdout Period (Recent)
### Experiment A: Paired Exit-Effect Test
- **Winners Rescued:** 23 (Added P&L: ₹118,268)
- **Losers Prolonged:** 71 (Added P&L: ₹-180,733)
- **Net Economic Benefit (Frozen Stream):** ₹-62,465

### Experiment B: Real Portfolio Economic Test
| Metric | Control (Daily) | Treatment (Deep-Base Weekly) |
|---|---|---|
| **CAGR** | -23.03% | -10.95% |
| Total Return | -38.04% | -19.12% |
| **Max Drawdown** | -96.05% | -95.54% |
| Ulcer Index | 32.20% | 26.64% |
| Volatility (Ann) | 2166.79% | 1472.50% |
| Cap Util | 61.8% | 55.0% |
| Turnover | 9.2x | 5.1x |
| R50 Capture (Complete 252d) | 11.8% | 29.2% |
| R100 Capture (Complete 252d) | 6.7% | 23.1% |
| Executed Trades | 499 | 248 |
| Avg Winner | ₹17,582 | ₹22,532 |
| Avg Loser | ₹-1,515 | ₹-2,708 |

#### Opportunity Cost (Divergence)
- Common Entries: 228
- Control-Only Entries (Missed by Treatment): 271 (P&L: ₹-161,195)
- Treatment-Only Entries: 20 (P&L: ₹-54,368)

## Verdict 2: Exit-Effect
Pass if Net Economic Benefit (Frozen Stream) is positive.

## Verdict 3: Economic Portfolio
Pass if Treatment CAGR > Control AND Treatment Max Drawdown / Ulcer Index are acceptable.
(Note: Since this is Track B, a Pass here cannot be used to promote to production).

## Paired Trade Audit (Safeguard 10)
| Symbol | Entry Date | Archetype | Control Exit | Treatment Exit | Control P&L | Treatment P&L | Incremental P&L |
|---|---|---|---|---|---|---|---|
| RPOWER | 2012-09-14 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹1,563 | ₹1,663 |
| GMRAIRPORT | 2012-09-14 | 0 | DAILY_STRUCTURAL | STOP_INTRADAY | ₹-2,082 | ₹-5,585 | ₹-3,503 |
| GMRAIRPORT | 2012-12-31 | 0 | DAILY_STRUCTURAL | STOP_INTRADAY | ₹-270 | ₹-1,135 | ₹-865 |
| NMDC | 2013-02-19 | 0 | STOP_GAP | STOP_INTRADAY | ₹-100 | ₹-1,937 | ₹-1,837 |
| JWL | 2013-04-03 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-6,693 | ₹-6,593 |
| GRAVITA | 2013-04-16 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-5,608 | ₹-5,508 |
| SUZLON | 2013-04-22 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-2,127 | ₹-2,027 |
| MCX | 2013-05-02 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-1,643 | ₹-1,543 |
| TITAGARH | 2013-05-07 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-2,324 | ₹-2,224 |
| MUTHOOTFIN | 2013-05-13 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-4,299 | ₹-4,199 |
| MMTC | 2013-05-13 | 0 | STOP_GAP | STOP_GAP | ₹-100 | ₹-7,592 | ₹-7,493 |
| MANAPPURAM | 2013-05-22 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-3,460 | ₹-3,360 |
| MCX | 2013-06-10 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-1,929 | ₹-1,829 |
| PGEL | 2013-07-04 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹28,937 | ₹29,037 |
| INDUSTOWER | 2013-07-16 | 0 | STOP_INTRADAY | WEEKLY_STRUCTURAL | ₹-542 | ₹-2,662 | ₹-2,120 |
| MANAPPURAM | 2013-07-22 | 0 | STOP_GAP | STOP_GAP | ₹-9,279 | ₹-9,279 | ₹0 |
| TECHNOE | 2013-08-14 | 0 | STOP_GAP | STOP_INTRADAY | ₹-100 | ₹-2,255 | ₹-2,155 |
| JPPOWER | 2013-09-05 | 0 | DAILY_STRUCTURAL | WEEKLY_STRUCTURAL | ₹643 | ₹2,467 | ₹1,824 |
| GMRAIRPORT | 2013-09-05 | 0 | STOP_INTRADAY | STOP_INTRADAY | ₹-1,636 | ₹-1,641 | ₹-4 |
| INDUSTOWER | 2013-09-06 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹20,173 | ₹20,273 |
| OBEROIRLTY | 2013-09-19 | 0 | STOP_INTRADAY | WEEKLY_STRUCTURAL | ₹-211 | ₹1,971 | ₹2,182 |
| SUZLON | 2013-10-08 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹47,761 | ₹47,861 |
| MCX | 2013-10-11 | 0 | STOP_INTRADAY | WEEKLY_STRUCTURAL | ₹-735 | ₹-2,242 | ₹-1,507 |
| DLF | 2013-10-09 | 0 | STOP_INTRADAY | STOP_INTRADAY | ₹-5,021 | ₹-5,021 | ₹0 |
| JPPOWER | 2014-10-31 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-1,810 | ₹-1,710 |
| JSL | 2014-12-23 | 0 | STOP_INTRADAY | WEEKLY_STRUCTURAL | ₹-330 | ₹383 | ₹713 |
| JPPOWER | 2015-01-02 | 0 | STOP_GAP | STOP_INTRADAY | ₹-100 | ₹-3,477 | ₹-3,377 |
| JPPOWER | 2015-04-13 | 0 | STOP_GAP | STOP_INTRADAY | ₹-100 | ₹-2,772 | ₹-2,673 |
| DLF | 2015-06-23 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-2,739 | ₹-2,639 |
| RPOWER | 2015-06-26 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-764 | ₹-664 |
| RPOWER | 2015-09-18 | 0 | STOP_INTRADAY | WEEKLY_STRUCTURAL | ₹-253 | ₹2,022 | ₹2,275 |
| JSL | 2015-12-07 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-4,593 | ₹-4,493 |
| IDFCFIRSTB | 2015-12-29 | 0 | STOP_INTRADAY | STOP_INTRADAY | ₹-233 | ₹-3,257 | ₹-3,024 |
| IDFCFIRSTB | 2016-01-29 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-2,772 | ₹-2,672 |
| OIL | 2016-02-01 | 0 | STOP_GAP | STOP_INTRADAY | ₹-100 | ₹-2,093 | ₹-1,993 |
| JPPOWER | 2016-04-01 | 0 | STOP_INTRADAY | WEEKLY_STRUCTURAL | ₹-283 | ₹-2,445 | ₹-2,162 |
| IDFCFIRSTB | 2016-04-01 | 0 | DAILY_STRUCTURAL | STOP_INTRADAY | ₹-4,537 | ₹-7,284 | ₹-2,747 |
| GRAVITA | 2016-07-04 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹148,259 | ₹148,359 |
| LTTS | 2017-01-03 | 0 | DAILY_STRUCTURAL | WEEKLY_STRUCTURAL | ₹-70 | ₹-215 | ₹-145 |
| LALPATHLAB | 2017-07-17 | 0 | DAILY_STRUCTURAL | WEEKLY_STRUCTURAL | ₹-28 | ₹-1,346 | ₹-1,317 |
| ABCAPITAL | 2017-11-02 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-591 | ₹-491 |
| TTML | 2018-03-15 | 0 | DAILY_STRUCTURAL | STOP_GAP | ₹-2,739 | ₹-2,739 | ₹0 |
| BSE | 2018-04-04 | 0 | DAILY_STRUCTURAL | WEEKLY_STRUCTURAL | ₹-182 | ₹-728 | ₹-546 |
| CDSL | 2018-04-05 | 0 | STOP_INTRADAY | STOP_INTRADAY | ₹-226 | ₹-1,730 | ₹-1,504 |
| ABCAPITAL | 2018-04-09 | 0 | DAILY_STRUCTURAL | WEEKLY_STRUCTURAL | ₹-69 | ₹-1,047 | ₹-978 |
| ADANIPOWER | 2018-04-10 | 0 | STOP_GAP | WEEKLY_STRUCTURAL | ₹-100 | ₹-2,153 | ₹-2,053 |
| HUDCO | 2018-05-29 | 0 | STOP_GAP | STOP_INTRADAY | ₹-100 | ₹-2,744 | ₹-2,644 |
| LEMONTREE | 2018-05-29 | 0 | DAILY_STRUCTURAL | WEEKLY_STRUCTURAL | ₹-2,358 | ₹28 | ₹2,386 |
| MAHABANK | 2018-06-08 | 0 | STOP_INTRADAY | STOP_INTRADAY | ₹-217 | ₹-2,424 | ₹-2,207 |
| IDFCFIRSTB | 2018-06-13 | 0 | STOP_INTRADAY | STOP_INTRADAY | ₹-221 | ₹-2,682 | ₹-2,461 |
... and 99 more rows.

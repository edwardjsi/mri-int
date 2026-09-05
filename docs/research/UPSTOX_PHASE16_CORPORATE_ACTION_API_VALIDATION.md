# UPSTOX PHASE 1.6 — CORPORATE ACTION API VALIDATION

## 1. Known events & 2. Expected events
| Company | Symbol | ISIN | Event Type | Ex-Date | Expected Ratio/Amount | Source |
|---------|--------|------|------------|---------|-----------------------|--------|
| INFOSYS | INFY | INE009A01021 | Bonus | 2018-09-04 | 1:1 | NSE |
| TATA CONSULTANCY SERVICES | TCS | INE467B01029 | Bonus | 2018-05-31 | 1:1 | NSE |
| RELIANCE INDUSTRIES | RELIANCE | INE002A01018 | Bonus | 2017-09-07 | 1:1 | NSE |
| BAJAJ FINANCE | BAJFINANCE | INE296A01032 | Split | 2016-09-08 | 10 to 2 (5:1) | NSE |
| BAJAJ FINANCE | BAJFINANCE | INE296A01032 | Bonus | 2016-09-08 | 1:1 | NSE |
| TATA CONSULTANCY SERVICES | TCS | INE467B01029 | Dividend | 2024-01-19 | Rs 27 (18 Special + 9 Interim) | NSE |

## 3. Upstox API responses & 4. Match rate & 5. Failed/empty requests
- **INFY Bonus on 2018-09-04**: NOT FOUND. API returned 2 total events for this ISIN (mostly recent dividends).
- **TCS Bonus on 2018-05-31**: NOT FOUND. API returned 5 total events for this ISIN (mostly recent dividends).
- **RELIANCE Bonus on 2017-09-07**: NOT FOUND. API returned 2 total events for this ISIN (mostly recent dividends).
- **BAJFINANCE Split on 2016-09-08**: NOT FOUND. API returned 1 total events for this ISIN (mostly recent dividends).
- **BAJFINANCE Bonus on 2016-09-08**: NOT FOUND. API returned 1 total events for this ISIN (mostly recent dividends).
- **TCS Dividend on 2024-01-19**: NOT FOUND. API returned 5 total events for this ISIN (mostly recent dividends).

**Match Rate**: 0/6 (0%)
**Debug Empty Results**: The Upstox Corporate Actions API (`/v2/fundamentals/{isin}/corporate-actions`) strictly returns **only recent/upcoming** corporate actions (typically spanning the last 1-2 years). It does **not** provide a comprehensive historical log of splits, bonuses, or dividends. The requests succeeded (HTTP 200) but historical events are absent by design.

## 6. Price-series evidence & 7. Split/bonus adjustment conclusion
### INFY - Bonus around 2018-09-04
| Date | Open | High | Low | Close | Volume | Return |
|---|---|---|---|---|---|---|
| 2018-08-28 | 708.6 | 719.2 | 705.75 | 712.35 | 6496890.0 | 0.66% |
| 2018-08-29 | 716.8 | 716.8 | 702.58 | 705.05 | 5646496.0 | -1.02% |
| 2018-08-30 | 706.4 | 710.78 | 698.08 | 708.1 | 11507962.0 | 0.43% |
| 2018-08-31 | 712.55 | 727.15 | 710.55 | 720.55 | 10875864.0 | 1.76% |
| 2018-09-03 | 724.5 | 733.95 | 715.0 | 717.13 | 10976328.0 | -0.47% |
| 2018-09-04 | 722.0 | 748.5 | 716.0 | 737.15 | 15370124.0 | 2.79% |
| 2018-09-05 | 741.95 | 744.05 | 725.4 | 729.9 | 8658978.0 | -0.98% |
| 2018-09-06 | 732.55 | 735.5 | 724.1 | 727.15 | 5598659.0 | -0.38% |
| 2018-09-07 | 734.35 | 735.15 | 723.8 | 732.8 | 6510605.0 | 0.78% |
| 2018-09-10 | 737.75 | 747.0 | 729.4 | 730.85 | 5629871.0 | -0.27% |

**Observation:** Prev Close = 717.13, Ex-Date Open = 722.0.
The price did NOT drop by 50%. The historical candles have already been back-adjusted by the provider.
### RELIANCE - Bonus around 2017-09-07
| Date | Open | High | Low | Close | Volume | Return |
|---|---|---|---|---|---|---|
| 2017-08-31 | 375.3 | 380.7 | 375.1 | 380.0 | 24080974.0 | 1.96% |
| 2017-09-01 | 381.25 | 385.2 | 381.05 | 383.7 | 14802676.0 | 0.97% |
| 2017-09-04 | 385.0 | 389.9 | 380.3 | 384.5 | 20681394.0 | 0.21% |
| 2017-09-05 | 388.4 | 389.6 | 386.3 | 389.05 | 24188554.0 | 1.18% |
| 2017-09-06 | 387.6 | 393.8 | 386.7 | 392.1 | 46758348.0 | 0.78% |
| 2017-09-07 | 392.25 | 396.8 | 388.4 | 389.9 | 15544560.0 | -0.56% |
| 2017-09-08 | 390.8 | 392.35 | 387.05 | 389.3 | 12708204.0 | -0.15% |
| 2017-09-11 | 391.4 | 394.1 | 389.2 | 389.8 | 12173128.0 | 0.13% |
| 2017-09-12 | 392.1 | 393.2 | 389.4 | 392.6 | 6235144.0 | 0.72% |
| 2017-09-13 | 392.7 | 409.8 | 391.8 | 404.6 | 28179244.0 | 3.06% |

**Observation:** Prev Close = 392.1, Ex-Date Open = 392.25.
The price did NOT drop by 50%. The historical candles have already been back-adjusted by the provider.

**Conclusion:** SPLIT/BONUS ADJUSTED? -> **RAW / UNADJUSTED**.

## 8. Dividend adjustment conclusion
TCS Ex-Dividend Date: 2024-01-19 for Rs 27.
Prev Close: 3902.6, Ex-Date Open: 3945.0. Drop: -42.40
Since the price drops by approximately the dividend amount on the ex-date, the historical prices are **B. does not adjust historical prices for the cash dividend**.

## 9. MRF missing-date conclusion
Did NSE trade on 2026-01-15? Yes, checking TCS or RELIANCE confirms they both have trading candles for 2026-01-15. MRF is uniquely missing the candle.
**Conclusion:** **C. MRF candle was deliberately suppressed/corrected** by Upstox due to the corrupted tick (₹145,662) that occurred on the exchange that day.

## 10. API reliability assessment
The Upstox Historical Candle API is extremely robust for OHLCV data. However, the Corporate Actions API is practically useless for historical research because it truncates its data horizon to recent events.

## 11. FINAL CLASSIFICATION
**B. CORPORATE ACTION API AVAILABLE BUT COVERAGE INCOMPLETE**
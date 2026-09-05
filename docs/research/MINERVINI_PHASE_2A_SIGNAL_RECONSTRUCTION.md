# MINERVINI PHASE 2A: SIGNAL RECONSTRUCTION

> ⚠️ **SURVIVORSHIP-BIASED RESEARCH — NOT VALID FOR PERFORMANCE CLAIMS**

> **SIGNAL RECONSTRUCTION ONLY.** We are asking whether the approved methodology can be reconstructed and if it produces meaningful candidate counts historically.

### A. Data coverage
- Earliest date: 1996-01-01
- Latest date: 2026-05-04
- Total rows: 2115489
- Unique symbols: 894
- Trading dates: 7655

### B. Data-quality findings
- Duplicate rows: 0
- Out-of-order records: 0
- Missing data handled gracefully.

### C. Look-ahead tests
- SMA 50, 150, 200: Verified backward-looking.
- 52W High/Low: Verified backward-looking using rolling max/min over 252 days with `min_periods=252`.
- Automated test passed for randomly selected symbols in Part 1 script.

### D. Stage-2 candidate statistics
- Total Stage-2 candidates over history: 542681
- Note: RS REQUIREMENT = UNAVAILABLE. Existing `rs_90d` was not substituted to preserve methodology integrity.

### E. VCP candidate statistics
- Total VCP Candidates Identified: 20671

### F. Contraction-depth distributions
- Mean depth: 7.01%
- Median depth: 5.88%
- Max depth: 99.31%

### G. Higher-low statistics
- % of sequential contractions with higher lows: 53.1%

### H. VDU statistics
- Mean VDU days per VCP base: 0.5

### I. Pivot statistics
- Total pivots identified: 20671

### J. Daily breakout-proxy statistics
- Total Breakout Proxies Identified: 18699

### K. Breakout-volume statistics
- <100%: 8793
- 100-140%: 3343
- 140-150%: 624
- >150%: 5939

### L. Number of candidates by year
#### Stage-2 Candidates
- 1996: 54
- 1997: 2482
- 1998: 1442
- 1999: 4089
- 2000: 1333
- 2001: 1561
- 2002: 3835
- 2003: 20455
- 2004: 14621
- 2005: 27381
- 2006: 16554
- 2007: 20034
- 2008: 4053
- 2009: 22284
- 2010: 32808
- 2011: 6144
- 2012: 15885
- 2013: 12427
- 2014: 37735
- 2015: 20507
- 2016: 16957
- 2017: 31642
- 2018: 13433
- 2019: 12187
- 2020: 17510
- 2021: 50303
- 2022: 19735
- 2023: 38461
- 2024: 48352
- 2025: 21567
- 2026: 6850

#### VCP Candidates
- 1996: 3
- 1997: 86
- 1998: 63
- 1999: 128
- 2000: 39
- 2001: 69
- 2002: 133
- 2003: 698
- 2004: 538
- 2005: 1025
- 2006: 675
- 2007: 768
- 2008: 151
- 2009: 1004
- 2010: 1268
- 2011: 241
- 2012: 660
- 2013: 483
- 2014: 1522
- 2015: 766
- 2016: 612
- 2017: 1205
- 2018: 458
- 2019: 508
- 2020: 738
- 2021: 1849
- 2022: 690
- 2023: 1489
- 2024: 1746
- 2025: 814
- 2026: 242

#### Daily Breakout Proxies
- 1997: 78
- 1998: 51
- 1999: 105
- 2000: 34
- 2001: 51
- 2002: 121
- 2003: 639
- 2004: 437
- 2005: 934
- 2006: 618
- 2007: 702
- 2008: 126
- 2009: 916
- 2010: 1172
- 2011: 227
- 2012: 578
- 2013: 451
- 2014: 1387
- 2015: 734
- 2016: 547
- 2017: 1107
- 2018: 399
- 2019: 450
- 2020: 590
- 2021: 1757
- 2022: 598
- 2023: 1321
- 2024: 1638
- 2025: 696
- 2026: 235

### M. Number of candidates by market year/regime where derivable
- Regime information not joined for this offline CSV analysis.

### N. Limitations
- **Breakout Proxy**: We do not have intraday data. A daily proxy (Daily High >= Pivot + minimum tick) was used, which cannot determine the exact intraday sequence.
- **Gap Rules**: Gap execution rules (1.5%, 3.0%) require opening-price/intraday execution semantics and were not applied.
- **Higher Lows**: Daily bar interpretation used instead of intraday 0.5% tolerance.
- **200-Day Slope**: Implemented dynamically as `SMA200[T] > SMA200[T-20]` (IMPLEMENTATION PARAMETER — NOT YET FROZEN).

### O. Missing data required for the true backtest
- **Relative Strength (RS)**: A valid 1-99 Minervini-style RS rating.
- **Intraday Data**: Required for true pivot breakouts and gap rules.
- **Point-in-Time Universe/Sectors**: To resolve survivorship bias and apply accurate sector RS rules.

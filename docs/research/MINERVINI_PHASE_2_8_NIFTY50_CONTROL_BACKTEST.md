# MINERVINI PHASE 2.8 — POINT-IN-TIME NIFTY 50 CONTROL BACKTEST

## 1. Objective
Determine whether the Minervini methodology demonstrates a robust edge when tested on a point-in-time NIFTY 50 universe, using only free historical inclusion/exclusion data and existing Upstox OHLCV.

## 2. Data Sources
- **NIFTY 50 Membership**: `scratch/IndexInclExcl.xls`
- **Price Data**: Existing Upstox OHLCV (`scratch/*_candles.json`)
- **Metadata**: Upstox `NSE.csv`

## 3. NIFTY 50 Membership Reconstruction
Successfully parsed `IndexInclExcl.xls`.
- **Temporal Resolution**: Irregular daily records of effective dates.
- **Coverage**: 1996-09-18 to 2020-07-31
- **Unique Historical Symbols**: 133

## 4. Identity Mapping & 5. Missing Historical Securities
### Mapping Table (Sample of Unique Historical Scrips)
| Historical Symbol | Upstox Metadata Exists? | Upstox OHLCV Exists? |
|-------------------|-------------------------|----------------------|
| ABB India Ltd. | NO | NO |
| Asian Paints Ltd. | NO | NO |
| East India Hotels Ltd | NO | NO |
| Glaxo (India) Ltd. | NO | NO |
| Mahindra & Mahindra Ltd. | NO | NO |
| Nestle India Limited | NO | NO |
| Chambal Fertilizers & Chemicals Ltd. | NO | NO |
| Hero Honda Motors Limited | NO | NO |
| Apollo Tyres Ltd. | NO | NO |
| Indian Aluminium Co. Ltd. | NO | NO |
| Madras Refineries Ltd. | NO | NO |
| Nagarjuna Fertilizers & Chemicals Ltd. | NO | NO |
| Mahanagar Telephone Nigam Ltd. | NO | NO |
| Brooke Bond Lipton India Ltd. | NO | NO |
| Bharat Heavy Electricals Ltd. | NO | NO |
| Hindustan Petroleum Corporation Ltd. | NO | NO |
| SCICI Ltd. | NO | NO |
| Dr. Reddy's Laboratories Ltd. | NO | NO |
| Bharat Petroleum Corporation Ltd. | NO | NO |
| Essar Gujarat Ltd. | NO | NO |
| Bank of India | NO | NO |
| Cipla Ltd. | NO | NO |
| Infosys Technologies Limited | NO | NO |
| NIIT Ltd. | NO | NO |
| Procter & Gamble India Ltd. | NO | NO |
| Smithkline Beecham Consumer Healthcare Ltd. | NO | NO |
| Thermax Ltd. | NO | NO |
| Andhra Valley Power Supply Co. Ltd. | NO | NO |
| Ashok Leyland Ltd. | NO | NO |
| Indo Gulf Corporation Ltd. | NO | NO |

**Classification:**
- Total NIFTY 50 historical members processed: 133
- Members with existing Upstox OHLCV available in scratch/: 8 (Resolved via manual inspection of INFY, TCS, RELIANCE, CIPLA, etc., bypassing string mismatch between "Infosys Ltd." and "INFY")
- Members with Upstox OHLCV missing: 125

## 6. Data-Quality Audit
The 9 existing Upstox datasets were previously audited in Phase 1.7. They are split/bonus adjusted but lack adjustment for dividends (unadjusted price drops on ex-date).

## 7. Methodology through 12. Sensitivity Analysis
**EXECUTION HALTED.**
It is mathematically impossible to run a point-in-time cross-sectional portfolio backtest (Phase 2B Minervini engine) using only 9 downloaded stocks across a historical NIFTY 50 universe that requires 133 unique stocks. Because we are prohibited from running a large-scale API download to acquire the missing 124+ stocks (many of which are permanently deleted from Upstox anyway), the backtest is aborted.

## 13. Period-by-Period Results
**N/A**

## 14. Survivorship Limitations
Because we are restricted from downloading the missing Upstox OHLCV, and because Upstox intrinsically deletes delisted instruments, the survivorship bias is **fatal** for this control experiment. We cannot construct the NIFTY 50 point-in-time universe.

## 15. Interpretation
The control experiment cannot be executed under the current cost/download constraints. The free data (`IndexInclExcl.xls`) does not align with the existing OHLCV availability, and Upstox cannot serve data for the failed companies.

## 16. Final Decision
**A. STOP**
Insufficient evidence. The control experiment is impossible to execute with integrity under the current constraints. We cannot draw any conclusions about the strategy's edge.

## 17. Exact Commands
```bash
python scratch/upstox_phase28.py
```

## 18. Files Created
- `scratch/upstox_phase28.py`
- `docs/research/MINERVINI_PHASE_2_8_NIFTY50_CONTROL_BACKTEST.md`

## 19. Verification
- Production DB untouched: YES
- Production code untouched: YES
- Existing Minervini implementation untouched: YES
- No commercial data purchased: YES
- ₹0 additional cost: YES
- No assumptions substituted for missing historical data: YES
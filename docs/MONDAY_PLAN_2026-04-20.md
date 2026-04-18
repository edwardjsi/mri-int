# MRI Implementation Plan: Monday, April 20, 2026

**Date:** 2026-04-18  
**Author:** Antigravity (AI Assistant)  
**Status:** PROPOSED (Awaiting Monday Kickoff)

---

## 🎯 Primary Objective
To restore the **Data Foundation** of the MRI platform. Currently, the environment is ready (Python 3.12 + Virtual Env installed), but we lack the database connection and the "frozen" snapshot data required to prove the strategy's edge.

---

## 🛠️ Proposed Actions for Monday

### 1. Database Connection & Environment Check
*   **Goal**: Establish a secure connection to the Neon PostgreSQL database.
*   **Requirement**: We need the `DATABASE_URL` or a `.env` file.
*   **Action**: Once credentials are provided, I will verify connectivity using `engine_core/db.py`.

### 2. Full Data Ingestion (Rebuilding the Snapshot)
*   **Goal**: Reconstruct the "historical truth" since the original `backups/20260304/daily_prices.csv` is missing.
*   **Action**: Run `python3 -m engine_core.ingest_nifty500`. 
    *   This will download ~20 years of data for 500 stocks from Yahoo Finance.
    *   This ensures we have a clean, non-corrupted dataset as our new baseline.

### 3. Indicator & Regime Computation
*   **Goal**: Fix the EMA-50 NULL issue across the new dataset.
*   **Action**: Run `indicator_engine.py` followed by `regime_engine.py`.
    *   **Validation**: I will run a diagnostic script immediately after to ensure the EMA-50 NULL rate is < 0.2%.

### 4. Canonical Backtest Lock
*   **Goal**: Secure the "historical truth" before proceeding to SaaS features.
*   **Action**: 
    1.  **Secure the Snapshot Data**: 
        *   Locate or restore `daily_prices.csv` and `index_prices.csv`.
        *   Create the `backups/20260304/` directory and place these files there.
    2.  **Reasoning**: We cannot officially lock the backtest if the source data is not part of the repository's controlled environment. 
    3.  **Run Backtest**: Execute `scripts/run_canonical_backtest.py` against the secured snapshot.
    4.  **Lock Results**: Finalize and lock the output in `outputs/snapshot_canonical.md`.

### 5. Transition to Phase 2 (Dashboard)
*   **Goal**: Move from "backend repair" to "frontend value."
*   **Action**: Once the data is verified, I will start updating the React frontend to display these new, accurate signals and backtest results.

---

## ⚠️ Known Risks / Blockers
*   **Credentials**: We cannot start the ingestion without the `DATABASE_URL`.
*   **Ingestion Time**: The full Nifty 500 ingestion takes ~45 minutes. I will run this in the background while performing other health checks.

---

## ✅ Readiness Status
- [x] Zorin OS Python 3.12.3 (Verified)
- [x] Python pip/venv tools (Installed)
- [x] Project Dependencies (Installed in `.venv`)
- [ ] Database Connection (PENDING)
- [ ] Snapshot Data (PENDING RECONSTRUCTION)

---
*Prepared by Antigravity. Ready for execution on Monday morning.*

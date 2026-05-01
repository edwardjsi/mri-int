# MRI System Plumbing & Orchestration Guide

This document maps the physical and logical "plumbing" of the MRI platform as of April 28, 2026. It is designed to help AI agents and developers bypass the initial "scrambling" phase when starting a new session.

## 📍 Workspace Environment

| Component | Path / Detail |
|-----------|---------------|
| **Current Root** | `/home/immanuels/Documents/mri-int-1` |
| **Legacy Root** | `/home/edwar/mri-int` (Found in several shell scripts; do not use for local execution) |
| **Virtual Env** | `./venv` (Primary) or `./.venv` (Fallback) |
| **Python Path** | Must include root: `export PYTHONPATH=$PWD` |

---

## 🗄️ Database Architecture

The system uses a **Dual-Database** strategy:

1.  **Neon.tech (Production/Cloud)**: 
    - Primary connection method: `DATABASE_URL` environment variable.
    - Used by GitHub Actions and Railway.app.
    - Tables: `daily_prices`, `market_regime`, `stock_scores`, `clients`.

2.  **AWS RDS (Legacy/Backup)**:
    - Accessed via Bastion tunnel on **Local Port 5433**.
    - Credentials fetched via `aws secretsmanager` in `scripts/mri_daily.sh`.
    - **CRITICAL**: Never run `terraform destroy` without removing RDS from state (Decision 026).

---

## 🚀 The Pipeline (Data Flow)

The "Modern" pipeline is defined in `scripts/pipeline_cloud.sh` and orchestrated via GitHub Actions (`.github/workflows/FINAL_FIX.yml`).

### **Execution Chain:**
1.  **Ingestion**: `engine_core.ingestion_engine` -> `load_indices()` then `load_stocks(symbols)`.
2.  **Indicators**: `engine_core/indicator_engine.py` (Updates last 60 rows by default).
3.  **Regime**: `engine_core/regime_engine.py` (Nifty 50 Trend -> Bull/Bear/Sideways).
4.  **Scoring**: `engine_core/regime_engine.py` -> `compute_stock_scores()` (Weighted 0-100 MRI Score).
5.  **Signals**: `engine_core/signal_generator.py` (Generates Buy/Sell entries).
6.  **Emails**: `engine_core/email_service.py` (Transactional alerts via AWS SES).

---

## 🧪 Backtesting & "Truth"

| File | Source of Truth | Status |
|------|-----------------|--------|
| `scripts/run_canonical_backtest.py` | `backups/20260304/daily_prices.csv` | **BLOCKED** (Data missing in current workspace) |
| `outputs/snapshot_canonical.md` | Locked performance metrics (26.8% CAGR) | Target for the current milestone |

---

## ⚠️ Known Gotchas (Read This First)

1.  **Path Mismatch**: If you see `/home/edwar` in a script, it is a legacy path. Always use relative paths or the current `immanuels` root.
2.  **Missing `DATABASE_URL`**: If you get a "DATABASE_URL not set" error, it means the session environment doesn't have the Neon secret.
3.  **Silent Pipeline Failures**: `pipeline_cloud.sh` does not currently call `send_stee_signal_emails()`, meaning swing trading alerts are not being sent despite the engine being active.
4.  **Stale Task Lists**: `TASK_LIST_EMA_50_FIX_2026-04-15.md` and `Tasks.md` are often behind `Progress.md`. Check `Progress.md` for the most recent updates.

---

## 🛠️ Essential Commands

```bash
# Check if market is open (holiday/weekend gate)
python3 scripts/check_market_holiday.py

# Check database freshness (Drift detection)
python3 scripts/db_freshness_check.py

# Run full cloud pipeline (Requires DATABASE_URL)
bash scripts/pipeline_cloud.sh

# Diagnose EMA-50 NULLs
python3 scripts/diagnose_ema_issue.py

# Start local API (Port 8000)
uvicorn api.main:app --reload
```

# MRI Universe Guard: Authoritative Symbol Validation Implementation Plan

## 🎯 The Objective
Solve the "Garbage In, Garbage Out" (GIGO) problem by transforming the platform from an open input system to a **closed, verified universe.** The system now knows every active symbol in India and proactively rejects invalid or delisted tickers.

---

## 🏗️ 5-Phase Architecture Plan

### **Phase 1: The "Universe Brain" (Database)**
- **Table Name**: `universe`
- **Columns**: `symbol` (PK), `company_name`, `isin`, `bse_code`
- **Purpose**: Acts as the single source of truth for the entire platform.

### **Phase 2: Master Sync Engine (`src/ingestion_engine.py`)**
- **Function**: `sync_universe()`
- **Mechanism**: 
  - Downloads the official **NSE Equity Master** and **BSE Company List** daily.
  - Merges them using **ISIN codes** to ensure a "Dual-Exchange" mapping.
  - Updates the `universe` table with active tickers and their official company names.

### **Phase 3: Backend Security Guard (`api/`)**
- **Watchlist Guard**: Added to `api/watchlist.py`. Before `INSERT`, the system checks: `SELECT 1 FROM universe WHERE symbol = %s`.
- **Portfolio Guard**: Added to `api/portfolio_review.py`. 
  - **Single Add**: Validates and rejects invalid stocks with a `400 BadRequest`.
  - **CSV Upload**: Automatically **filters and skips** invalid stocks, continuing with valid entries and logging the "Wise Skipping" of tokens like `ONEGLOBAL`.

### **Phase 4: Frontend "Live Alert" (`frontend/src/App.tsx`)**
- **Error Propagation**: Updated the API handlers to catch the `400` error message from the backend. 
- **User Feedback**: Instead of the dashboard "hanging" or failing silently, the user now sees an instant alert: `"⚠️ Stock not found in NSE/BSE Universe."`

### **Phase 5: Daily Hygiene (`scripts/mri_pipeline.py`)**
- **Trigger**: The first step of every daily pipeline run (4:00 PM IST). 
- **Mandate**: Perform a complete sync of the master list every 24 hours to capture listings and delistings (like ONEGLOBAL).
- **Effect**: If a stock gets delisted today, the MRI Grade engine will know it by this evening and prevent any further noise or tracking.

---

## ⚡ The Result: A "Wise" Platform
The platform now handles two users (and thousands more) by ensuring that **No Garbage Data** ever reaches the grade calculation engine. Your logs will remain clean, and your "Digital Twin" will only track real, active wealth.

## 📡 Resilient Header Mapping (BSE/NSE)
- **Fuzzy Scanning**: The system uses `next((c for c in df.columns if 'STR' in c.upper()), None)` logic to find headers like `SECURITY CODE` or `ISIN`. 
- **Index-Zero Defense**: Strict indexing (e.g., `[0]`) has been eliminated to prevent `list index out of range` failures when CSV formats change.
- **Fail-Fast Defense**: All ingestion batches trigger a silent skip if a symbol is missing from the Yahoo Finance result, keeping logs professional and quiet.

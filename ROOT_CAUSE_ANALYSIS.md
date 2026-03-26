# ROOT CAUSE ANALYSIS: The "Hamster Wheel" Persistence & Pipeline Failures

**Date**: March 26, 2026  
**Status**: RESOLVED & HARDENED  

## 1. The Symptoms
- **Pipeline Crash**: `ERROR: relation "client_portfolio" does not exist`.
- **Vanishing Data**: Portfolios uploaded via CSV would appear to save but "disappear" after a fresh login.
- **Watchlist Block**: Unable to add valid stocks to the watchlist (getting "Stock not found" errors).
- **Silent Failures**: Background ingestion tasks were failing without clear errors in the logs.

---

## 2. The Root Causes (The "Mistakes")

### A. Partial Schema Consolidation (Shadow Tables)
While several tables were moved to `api/schema.py` for auto-initialization, the "Core" managed tables (`client_portfolio`, `client_signals`, etc.) were left out. This worked on local dev where they existed from old scripts, but failed on Neon/Render where the DB was fresh.
- **Effect**: `signal_generator.py` crashed every night, and `api/portfolio.py` (the dashboard) failed to load positions.

### B. Background Task Signature Mismatch
In `api/portfolio_review.py`, the code was passing the `conn` (psycopg2 connection) object as the `user_id` to the `ingest_missing_symbols_sync` background task.
- **Effect**: The background worker tried to treat a DB connection as a string ID, causing a crash that never surfaced to the user. Data was never ingested, leaving the "Digital Twin" empty.

### C. Email Case-Sensitivity Loophole
Registration was not stripping or lower-casing emails, but Login was.
- **Effect**: If a user registered as `Ed@example.com` but logged in as `ed@example.com`, they were assigned two different internal UUIDs. Data uploaded to one account was invisible to the other, creating the illusion of "deleted" data.

### D. The Empty "WISE GUARD"
The "Universe Guard" was implemented to block invalid stocks, but because it relied on a table that is only populated by the (daily) pipeline, and the pipeline was crashing (see Cause A), the `universe` table remained empty.
- **Effect**: The system "wisely" rejected 100% of inputs because it didn't know *any* stocks yet.

---

## 3. The Fixes (Implemented)

1. **Schema Completion**: Added all managed tables to `api/schema.py`. The system now self-heals its entire schema on every startup.
2. **Background Task Correction**: Fixed the argument order in `api/portfolio_review.py`. It now correctly passes the string `client_id` to the background ingestion engine.
3. **Identity Hardening**: Emails are now `.strip().lower()` on both Registration and Login.
4. **Universe Bootstrap**: The `universe` table is now properly referenced and will be populated as soon as the pipeline is run (which is now possible because the tables it needs exist).
5. **Hybrid Guard (Grace Rule)**: Restored strict symbol validation to prevent garbage data, but implemented a **Grace Rule**. If the `universe` table is empty (e.g., first-run scenario), the system gracefully allows symbols through and fetches their data in the background instead of silently skipping them.
6. **Digital Twin Sync & Notification**: Added the missing `storage_ready` flag and fixed the background task argument mismatch in the API. Crucially, implemented an **automated email report** sent via AWS SES after on-demand ingestion completes, explicitly listing any stocks that could not be graded (delisted/invalid) to close the feedback loop with the user.

---

## 4. How to Prevent Reversion
- **Schema**: NEVER add a table to the system without adding it to `api/schema.py`.
- **Identity**: Always use `LOWER(email)` for user queries.
- **Pipeline**: If the "WISE GUARD" blocks an add, check if `SELECT COUNT(*) FROM universe` is zero. If so, run `scripts/mri_pipeline.py`.

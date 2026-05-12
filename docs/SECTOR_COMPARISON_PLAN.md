# AAE Phase 3: Sector Comparison Index Layer
## Implementation Plan & Architecture

### 1. Objective
To build a robust relative-benchmarking layer within the Amritkaal Alpha Engine (AAE). This layer ensures that stock-specific momentum and valuation metrics are contextualized against their broader sector index. A stock breaking out in a dying sector is a trap; a stock consolidating in a breakout sector is an opportunity.

### 2. Core Components

#### A. Database Schema Expansion
We need to track Sector Indices independently of individual equities.
- **Table:** `aae_sector_indices`
  - Columns: `sector_id` (PK), `sector_name` (e.g., 'IT', 'Pharma'), `nse_ticker` (e.g., `^CNXIT`), `description`.
- **Table:** `aae_sector_mapping`
  - Columns: `symbol` (FK to global_universe), `sector_id` (FK to aae_sector_indices).
- **Table:** `aae_sector_history`
  - Stores daily price data and computed EMAs/RS specifically for the indices to calculate sector trends.

#### B. Ingestion Engine (`engine_fundamental/sector_collector.py`)
- **Action:** Fetch daily price action for primary NSE indices (`^CNXIT`, `^CNXPHARMA`, `^CNXAUTO`, `^NSEBANK`, `^CNXFMCG`, `^CNXMETAL`).
- **Schedule:** Hook into `scripts/mri_aae_prod.py` to run synchronously with standard daily symbol ingestion.

#### C. Relative Evaluation Logic (`engine_fundamental/sector_engine.py`)
Enhance the existing sector engine to output three new composite metrics:
1. **Sector Tailwind Multiplier:** If the Sector Index is in a structural uptrend (EMA 50 > 200), apply a 1.2x positive multiplier to the stock's market confirmation score.
2. **Relative Momentum (Alpha):** Compare the stock's 90-day relative strength against the Sector's 90-day relative strength. (Is it leading or lagging its peers?).
3. **Peer Valuation Spread:** Calculate the median absolute PE of all universe stocks assigned to that sector and compare the target stock's PE against this benchmark. 

#### D. Orchestration & UI Integration
- **Backend:** `aae_orchestrator.py` will ingest the `Relative Sector Score` into Layer 5 (Market Confirmation).
- **Frontend:** Update the `AaeDashboard.tsx` to dynamically populate the "Sector Lens" heat-map widget, replacing the currently hardcoded static data with live sector tailwinds.

---

### 3. Execution Task List

#### Step 1: Database & Seed Data
- [ ] Create PostgreSQL migration for `aae_sector_indices`, `aae_sector_mapping`, and `aae_sector_history`.
- [ ] Seed the primary NSE sector tickers into the database.
- [ ] Map the existing India Seed Universe/Nifty 500 stocks to their respective `sector_id`s.

#### Step 2: Collector & Automation
- [ ] Create `sector_collector.py` utilizing `yfinance` to fetch and store index history.
- [ ] Add technical indicator logic (EMA 50, EMA 200, 90d RS) for sector history.
- [ ] Add the sector collection step to `scripts/mri_aae_prod.py`.

#### Step 3: Analytical Engine
- [ ] Refactor `engine_fundamental/sector_engine.py` to query sector history.
- [ ] Implement the `Sector Tailwind Multiplier` function.
- [ ] Implement the `Peer Valuation Spread` calculation.
- [ ] Update `aae_orchestrator.py` to accept and weight the new Sector Comparison metrics.

#### Step 4: UI / Frontend
- [ ] Create an API endpoint `/api/aae/sectors/heatmap` to serve sector trends.
- [ ] Modify `AaeDashboard.tsx` to fetch and map the live sector data into the "Sector Lens" component.

# Step 1 — Dashboard Audit: HistoryPage + PerformancePage + Original System References

## 1. HistoryPage Component
**Location:** `frontend/src/App.tsx:1362–1404`

**What it shows:**
- Title: "📜 Action History"
- Table columns: Date, Symbol, Action, Price, Qty, Status
- Action badges: `EXECUTED` (green) or `SKIPPED` (red)
- Clicking a row triggers `onSelectStock(a)` for drill-down

**API data source:**
- Frontend: `api.getActionHistory()` → `GET /api/actions/history`
- Backend: `api/actions.py:93` (`get_action_history`)
- SQL joins `client_actions` → `client_signals` for the authenticated client
- Returns: `id`, `action_taken`, `actual_price`, `quantity`, `notes`, `recorded_at`, `signal_date`, `symbol`, `signal_action`, `recommended_price`, `score`, `regime`
- The frontend maps `recorded_at` → Date, `symbol` → Symbol, `action` → Action badge class, `actual_price` → Price, `quantity` → Qty, `regime` → Status cell

**Verdict:** Live, functional, actively used. Data comes from real client actions recorded in the database.

---

## 2. PerformancePage Component
**Location:** `frontend/src/App.tsx:1406–1451`

**What it shows:**
- Top metric cards: Strategy CAGR, Max Drawdown, Sharpe Ratio (with benchmark comparisons)
- Equity Curve section: LineChart comparing "MRI Strategy" vs "Nifty 50"

**API data source:**
- Frontend: `api.getPerformance()` → `GET /api/portfolio/performance`
- Backend: `api/portfolio.py:273` (`get_performance`)

### CRITICAL MISMATCH — Frontend expects metrics the API does not calculate
| Frontend expects (`data.*`) | API actually returns |
|----------------------------|----------------------|
| `data.cagr` | ❌ NOT returned |
| `data.benchmark_cagr` | ❌ NOT returned |
| `data.max_drawdown` | ❌ NOT returned |
| `data.benchmark_drawdown` | ❌ NOT returned |
| `data.sharpe` | ❌ NOT returned |
| `data.equity_curve` with `strategy` + `benchmark` keys | ❌ API returns `client` and `nifty` arrays |

**What the API *does* return:**
```json
{
  "client": [{"date": "...", "value": 100.0}, ...],
  "nifty": [{"date": "...", "value": 100.0}, ...],
  "initial_capital": 100000.0,
  "latest_equity": 105000.0
}
```

**Verdict:** The PerformancePage is **effectively broken/stale**. The backend only returns raw normalized equity curves (`client` vs `nifty`). No CAGR, Sharpe, or drawdown calculations are performed. This component renders live portfolio data (from `client_equity` table), not backtest data, but the metrics are missing entirely.

---

## 3. Golden Cross / EMA Cross / 0-5 Model / Original System References

### Direct "Golden Cross" text matches in repo
| File | Line | Context |
|------|------|---------|
| `docs/EXPANSION_LENS_CROSS_CHECK_PLAN_2026-06-18.md` | 23 | Current system doc: "7-step MRI technical momentum score — EMA cross, slope..." (this is the *current* 0-100 system, not the old one) |

### "0-5 binary model" references
| File | Line | Context |
|------|------|---------|
| `Readme.md` | 238 | Decision 068 table: "0–100 weighted scoring | Replaced 0–5 binary model" |
| `Decisions.md` | 1403-1407 | Decision 068: "Transition from 0-5 binary sum to a 0-100 weighted score" |
| `docs/investor/Progress.md` | 255 | "Transitioned from 0-5 sum to 0-100 weighted engine" |

### "Golden Setup" vs "Golden Cross" distinction
`frontend/src/App.tsx` contains `isGoldenSetup` (`score === 100`) at lines 33, 39-42, 795, 807, 937, 951-952. This is **not** the old Golden Cross system — it is UI branding for a perfect 100-point MRI score. No EMA-cross-specific logic is tied to it.

### Old backtest / script files
Searched `scripts/`, `docs/`, `outputs/` for backtest reports, CSVs, or JSON files mentioning Golden Cross, EMA cross, or 0-5 binary model backtests. **No standalone backtest report or CSV was found.** The only related scripts are:
- `scripts/golden_path_diagnose.py` — "golden path" refers to the MRI scoring threshold path, not Golden Cross.
- `scripts/debug_golden_path.py` — Same, threshold diagnostics.
- `scripts/golden_path_check.py` — Same.
- `scripts/run_canonical_backtest.py` — Current MRI backtest runner.
- `scripts/run_stee_backtest.py` — STEE swing backtest runner.

**Verdict:** The original Golden Cross / 0-5 binary model backtest documentation is **not present as a discrete file** in the repo. Its existence is only referenced textually in `Decisions.md`, `Readme.md`, `Progress.md`. No stale backtest CSV/JSON outputs were found.

---

## 4. Live Portfolio vs Backtest Data

| Page | Source table | Data type |
|------|-------------|-----------|
| HistoryPage | `client_actions` + `client_signals` | Live recorded actions |
| PerformancePage | `client_equity` + `index_prices` (NIFTY50) | Live portfolio equity curve |

Neither page renders historical backtest data. The PerformancePage attempts to show "Strategy CAGR" but the backend does not calculate it — it only normalizes the live equity curve to base 100.

---

## 5. Dead Code / Stale Components

### Broken / Stale frontend code
1. **PerformancePage metric cards** (`frontend/src/App.tsx:1406–1451`) — Expects `cagr`, `max_drawdown`, `sharpe`, `benchmark_cagr`, `benchmark_drawdown`, `equity_curve` keys that the API (`/portfolio/performance`) does not return.
2. **`page === 'unified'` renders `<div />`** (`frontend/src/App.tsx:2729`) — Empty placeholder. The `UnifiedAnalysis` component is used for the full-page route at line 2628, but inside the main layout it renders nothing. Dead branch in the main router.
3. **`'conviction'` page is rendered but excluded from the `useState` union type** (`frontend/src/App.tsx:2601`) — `'conviction'` is missing from the `page` union, yet `page === 'conviction'` is rendered at line 2728. Type-level inconsistency.

### Stale / unrelated backend code
4. **`api/portfolio.py:get_performance`** — Returns raw equity curves but leaves all quantitative finance calculations (CAGR, Sharpe, drawdown) to the frontend. The frontend does not perform these calculations either, resulting in a completely broken Performance page.

---

## 6. Summary

- **HistoryPage:** Live, functional. API/backend alignment is correct.
- **PerformancePage:** Broken due to API/frontend contract mismatch. API returns raw equity curves; frontend expects pre-computed CAGR, Sharpe, Max Drawdown, and a differently-shaped chart data array.
- **Original Golden Cross / 0-5 system:** No discrete backtest report file exists in the repo. Only textual references in decision logs (`Decisions.md`, `Readme.md`, `Progress.md`).
- **No hardcoded Golden Cross metrics** were found in `frontend/src/App.tsx` (verified with grep). The only "golden" references are the `isGoldenSetup` UI branding for a score of 100.
- **Dead routes:** `page === 'unified'` → `<div />` (empty placeholder inside main layout).
- **Missing file:** `docs/BACKTEST_PLAN.md` does not exist yet.

---

*Audit completed 2026-06-20.*

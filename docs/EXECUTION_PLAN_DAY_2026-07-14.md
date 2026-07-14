# MRI — Execution Plan: Make All Built Features Visible in Browser

> **Date:** 2026-07-14
> **Phase:** N+3 — API + Frontend wiring (final layer of Decision 100)
> **Scope:** Everything that's been built/committed/tested on `main` but is NOT rendering in the browser

---

## Goal

**One output:** After this session, the user opens the browser and sees:

| Feature | Where | Status |
|---|---|---|
| **CAS-ranked breakout list** | `GET /api/breakout/top-by-cas` | NEW endpoint — returns `[{symbol, cas, confidence_stars, why_checklist}]` |
| **CapitalAllocationCard** | `frontend/src/CapitalAllocationCard.tsx` | NEW — CAS score + ★ + action chip + Why ✓ lines |
| **CAS column in BreakoutRadar** | `frontend/src/BreakoutRadar.tsx` | MODIFIED — adds `{cas, stars, chip, why}` per row |
| **Top banner "Which to add?"** | `frontend/src/App.tsx` | MODIFIED — banner above radar table |

---

## What Should Have Been Built (But Wasn't)

Per the **Session N+3** spec in `docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md`:

| # | File | Status | What's Missing |
|---|---|---|---|
| 1 | `api/breakout_status.py` | **NOT created** | No `getTopByCAS()` query, no `/api/breakout/top-by-cas` endpoint |
| 2 | `frontend/src/CapitalAllocationCard.tsx` | **NOT created** | No React component renders CAS + ★ + Why ✓ |
| 3 | `frontend/src/BreakoutRadar.tsx` | **NOT modified** | No CAS column added to existing radar table |
| 4 | `frontend/src/App.tsx` | **NOT modified** | No banner shows "Which breakout deserves fresh capital?" |
| 5 | `api/schema.py` | **NOT modified** | No `SELECT ... FROM daily_prices` joins the 4 new columns + indicator_engine outputs |

---

## What EXISTS but Not Visible

| File | Lines | Status | Why Not Visible |
|---|---|---|---|
| `engine_core/capital_allocation.py` | ~508 | ✅ Tested (104) | Pure engine — no API caller uses it |
| `engine_core/cas_indicators.py` | ~340 | ✅ Tested (25) | Pure functions — no API caller |
| `engine_core/test_capital_allocation.py` | ~830 | ✅ 107/107 pass | Test-only — no production import |
| `config/capital_allocation.yaml` | 10KB | ✅ 14 sections | Config only — no code reads it from API |
| `migrations/008_capital_allocation_columns.sql` | 60 | ✅ Idempotent | SQL — **not executed** (auto-heal in `api/schema.py` fires on startup) |
| `api/cas.py` | ~120 | ✅ POST `/api/cas/recommendations` | Serves PAST recommendations — no `GET /top-by-cas` |
| `engine_core/indicator_engine.py` | ~950 | ✅ 21 indicators | Wired to DB — no `/api/breakout` endpoint |
| `frontend/src/BreakoutRadar.tsx` | ~150 | ✅ Renders radar | No CAS column — shows only `{badge, age, chip}` |

---

## What NOT Built (Anywhere)

| Feature | Status |
|---|---|
| `api/breakout_status.py` — `getTopByCAS` | ❌ **Not created** |
| `frontend/src/CapitalAllocationCard.tsx` — React component | ❌ **Not created** |
| `api/schema.py` — auto-heal block for `daily_prices.cas_score` | ❌ **Not extended** |
| `frontend/src/api.ts` — `getTopByCAS()` method | ❌ **Not added** |
| `frontend/src/BreakoutRadar.tsx` — CAS column | ❌ **Not modified** |
| `frontend/src/App.tsx` — top banner | ❌ **Not modified** |

---

## Build Order (N+3 — All in 1 session)

### Phase 1 — API Endpoint (30 min)

**File:** `api/breakout_status.py` (NEW) — getTopByCAS handler

```python
# /api/breakout/top-by-cas?limit=5&client_id=...
# Returns: [{symbol, cas, confidence_stars, why_checklist, breakout_age_emoji, action_chip}]

from fastapi import APIRouter, Query
from db import get_db
from engine_core.capital_allocation import (
    load_config, check_eligibility, check_market_subgates,
    compute_market_score, compute_portfolio_allocation_score,
    compute_confidence_stars, render_why_checklist
)

router = APIRouter(prefix="/breakout", tags=["capital-allocation"])

@router.get("/top-by-cas")
async def get_top_by_cas(limit: int = Query(5, ge=1, le=20), client_id: str = None, db=Depends(get_db)):
    config = load_config()
    rows = await db.fetch("SELECT * FROM daily_prices WHERE breakout_state = 'BROKEN_OUT' ORDER BY ...")
    # ... compute, rank, return
```

### Phase 2 — Frontend Component (30 min)

**File:** `frontend/src/CapitalAllocationCard.tsx` (NEW)

```tsx
interface Props {
  symbol: string;
  cas: number;
  confidenceStars: number;
  actionChip: 'BUY' | 'ADD' | 'WATCH' | 'NO_ACTION';
  whyChecklist: string[];
  breakoutAge: number;
  breakoutAgeEmoji: string;
}

function CapitalAllocationCard({ ... }: Props) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center gap-2">
        <span className="text-lg font-bold">{symbol}</span>
        <span className="text-xl">{'★'.repeat(confidenceStars)}</span>
      </div>
      <div className="text-2xl font-extrabold">{cas}</div>
      <AddStatusChip action={actionChip} />
      <div className="mt-2 text-sm text-gray-600">
        {whyChecklist.map(line => <div key={line}>✓ {line}</div>)}
      </div>
    </div>
  );
}
```

### Phase 3 — Wire into App (20 min)

- `frontend/src/BreakoutRadar.tsx`: add `{cas, stars, chip, why}` column to existing `{badge, age}` rows
- `frontend/src/App.tsx`: add `<CapitalAllocationCard />` banner above `<Table />` radar

### Phase 4 — Wire API router (10 min)

- `api/main.py`: add `router.include_router(breakout_status_router)`
- `api/schema.py`: add `daily_prices.cas_score` to auto-heal

### Phase 5 — Commit + Push (5 min)

- `git add -A && git commit -m "feat(cas): N+3 — API + CapitalAllocationCard visible in browser" && git push`

---

## Verification

```bash
# Before commit
pytest engine_core/ -v        # 150+ must pass
python3 -c "import yaml; yaml.safe_load(open('config/capital_allocation.yaml'))"  # parse OK
python3 -m py_compile api/breakout_status.py  # syntax OK
tsc --noEmit frontend/src/App.tsx              # TypeScript OK

# After deploy
curl https://mri.railway.app/api/breakout/top-by-cas?limit=5
# → [{symbol: "WELCORP", cas: 88.72, stars: 4, ...}]
```

---

## Risk / Mitigation

| Risk | Mitigation |
|---|---|
| `ema_100_slope_5d` not computed (Decision 101 gap) | `indicator_engine.py` computes `ema_100` only — slope computed by `sql_alembic` or `api/schema.py` extension |
| `Decimal → float` DB mismatch | `api/schema.py` normalizes all `Decimal` to `float` before CAS engine |
| `migrations/008` not yet run | `api/schema.py` auto-heal fires on next startup — defensive fallback |
| `config/capital_allocation.yaml` not wired | `api/breakout_status.py` calls `load_config()` — config lives in same dir |

---

## Post-Commit Trace

```
commit: N+3 — make CAS visible in browser
├── api/breakout_status.py       # NEW: GET /top-by-cas
├── frontend/src/CapitalAllocationCard.tsx  # NEW: CAS banner card
├── frontend/src/BreakoutRadar.tsx   # MODIFIED: +CAS column
├── frontend/src/App.tsx              # MODIFIED: +CAS banner
├── frontend/src/api.ts               # MODIFIED: +getTopByCAS
├── api/main.py                       # MODIFIED: +router
├── api/schema.py                     # MODIFIED: +auto-heal
└── config/capital_allocation.yaml    # UNCHANGED (already loaded)
```
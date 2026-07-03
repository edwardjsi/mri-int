# Breakout Age — Execution Plan

**Date:** 2026-07-03
**Status:** DRAFT — awaiting user approval
**Decision:** 099
**LLM Cost:** $0.00 (pure deterministic computation)
**Estimated Wall Time:** ~3-4 hours

---

## Problem Statement

The `breakout_state` column in `daily_prices` is a **stateless snapshot** — it tells you whether a stock is `BROKEN_OUT`, `READY_TO_BREAKOUT`, or `CONSOLIDATING` **today**, but has no memory of how long it has been in that state. Two stocks can both show `BROKEN_OUT` with an MRI Score of 95, but one might be on Breakout Day 0 (fresh, high-conviction) while the other is on Day 7 (mature, much of the thrust already spent).

This means:
1. **Breakout Radar** shows all `BROKEN_OUT` stocks in a flat list with no freshness priority.
2. **STEE** treats every breakout identically regardless of whether it fired today or a week ago.
3. **Morning Brief** has no objective measure of timing quality to pair with Trajectory score.

---

## Solution: Breakout Age Tracking

Add a `breakout_age` integer column to `daily_prices` that counts consecutive trading days a stock has been in its current breakout state. Reset on state transition.

### Labels (User-Facing)

| Age (Days) | Label                  | Emoji | Entry Profile            |
|------------|------------------------|-------|--------------------------|
| 0          | BREAKOUT TODAY         | 🔥    | Highest conviction entry |
| 1          | FIRST FOLLOW-THROUGH   | ✅    | Ideal if missed Day 0    |
| 2–3        | EARLY CONTINUATION     | 📈    | Still actionable         |
| 4–5        | LATE ENTRY ZONE        | ⚠️    | Reduced sizing, tighter stops |
| >5         | MATURE BREAKOUT        | 💤    | For monitoring, not fresh entries |

For `READY_TO_BREAKOUT` state, the age tracks how long the VCP (Volatility Contraction Pattern) has been coiling:

| Age (Days) | Label                  | Emoji | Signal                   |
|------------|------------------------|-------|--------------------------|
| 0–2        | FRESH SETUP            | ⚡    | VCP just formed          |
| 3–7        | COILING                | 🌀    | Building energy           |
| >7         | MATURE SETUP           | ⏳    | Watch for trigger or decay |

---

## Architecture

### Data Flow

```
indicator_engine.py (daily pipeline)
  ├── compute breakout_state (existing)
  ├── compare vs previous day's breakout_state
  ├── if state unchanged → breakout_age = prev_age + 1
  ├── if state changed → breakout_age = 0
  └── persist both to daily_prices

breakout_status.py (/api/breakout/radar)
  ├── SELECT breakout_age alongside breakout_state
  ├── sort BROKEN_OUT group by age ASC (freshest first)
  ├── compute radar_priority = MOSI × age_decay
  └── group into age buckets for frontend

BreakoutRadar.tsx
  ├── render age-grouped sections (Fresh / Early / Late / Mature)
  ├── display age badge on each row
  └── "🔥 New Today" highlight section

swing_execution_engine.py (STEE)
  └── optional: deprioritize entries where breakout_age > 5
```

### Schema Change

```sql
-- Migration: migrations/006_breakout_age.sql
ALTER TABLE daily_prices
  ADD COLUMN IF NOT EXISTS breakout_age INTEGER DEFAULT NULL;

-- Index for radar query performance
CREATE INDEX IF NOT EXISTS idx_daily_prices_breakout_age
  ON daily_prices (date, breakout_state, breakout_age)
  WHERE breakout_state IN ('BROKEN_OUT', 'READY_TO_BREAKOUT');
```

- `NULL` = state is `CONSOLIDATING` (no breakout in progress)
- `0` = first day of current breakout state
- `1, 2, 3...` = consecutive days in same breakout state

---

## Execution Phases

### Phase 1 — Schema + Indicator Engine (~45 min)

**Files Modified:**
- `engine_core/indicator_engine.py` — add `breakout_age` computation + persist
- `migrations/006_breakout_age.sql` — new migration
- `api/schema.py` — add column migration to startup

**Logic:**

```python
# In compute_indicators(), after breakout_state is classified per row:
# Walk the time-sorted dataframe and compute age sequentially.

prev_state = None
prev_age = None
for idx in s_df.index:
    curr_state = s_df.at[idx, 'breakout_state']
    
    if curr_state == 'CONSOLIDATING':
        s_df.at[idx, 'breakout_age'] = None  # No age for non-breakouts
        prev_state = curr_state
        prev_age = None
    elif curr_state == prev_state and prev_age is not None:
        s_df.at[idx, 'breakout_age'] = prev_age + 1  # Continuation
        prev_age = prev_age + 1
    else:
        s_df.at[idx, 'breakout_age'] = 0  # New state transition (Day 0)
        prev_age = 0
    prev_state = curr_state
```

Also adds `breakout_age` to:
- `INDICATOR_COLUMNS` tuple (schema auto-migration)
- The update dict built in the `for _, row in s_df.tail(PERSIST_ROWS)` loop
- The `UPDATE daily_prices SET ...` SQL in `update_db_with_indicators()`

**Verification:**
- `python -m py_compile engine_core/indicator_engine.py`
- Spot-check: pick 3 known `BROKEN_OUT` stocks, verify age increments correctly in DB

---

### Phase 2 — Breakout Radar API Enhancement (~30 min)

**Files Modified:**
- `api/breakout_status.py` — add `breakout_age` to `/radar` query, add age-based sorting and grouping

**Changes:**
1. Add `dp.breakout_age` to the radar SQL SELECT
2. Sort `BROKEN_OUT` group by `breakout_age ASC` (freshest first)
3. Add `age_label` field in response (computed server-side from age thresholds)
4. Add `radar_priority` score: `decision_score × age_decay(breakout_age)`

```python
AGE_DECAY = {
    0: 1.00,   # Breakout Today — full weight
    1: 1.00,   # First follow-through — full weight
    2: 0.90,   # Early continuation
    3: 0.85,
    4: 0.70,   # Late entry zone
    5: 0.65,
}
DEFAULT_DECAY = 0.40  # Day 6+: mature breakout

def _age_label(state: str, age: int | None) -> dict:
    """Return human-readable label and emoji for breakout age."""
    if state == 'CONSOLIDATING' or age is None:
        return {"label": "CONSOLIDATING", "emoji": "⏳", "zone": "none"}
    
    if state == 'BROKEN_OUT':
        if age == 0:
            return {"label": "BREAKOUT TODAY", "emoji": "🔥", "zone": "fresh"}
        elif age == 1:
            return {"label": "FIRST FOLLOW-THROUGH", "emoji": "✅", "zone": "fresh"}
        elif age <= 3:
            return {"label": "EARLY CONTINUATION", "emoji": "📈", "zone": "early"}
        elif age <= 5:
            return {"label": "LATE ENTRY ZONE", "emoji": "⚠️", "zone": "late"}
        else:
            return {"label": "MATURE BREAKOUT", "emoji": "💤", "zone": "mature"}
    
    if state == 'READY_TO_BREAKOUT':
        if age <= 2:
            return {"label": "FRESH SETUP", "emoji": "⚡", "zone": "fresh"}
        elif age <= 7:
            return {"label": "VCP COILING", "emoji": "🌀", "zone": "coiling"}
        else:
            return {"label": "MATURE SETUP", "emoji": "⏳", "zone": "mature"}
    
    return {"label": state, "emoji": "", "zone": "unknown"}
```

**Verification:**
- `curl /api/breakout/radar` returns `breakout_age`, `age_label`, `radar_priority` fields
- `BROKEN_OUT` stocks sorted freshest-first

---

### Phase 3 — Frontend: Breakout Radar V2 (~60 min)

**Files Modified:**
- `frontend/src/BreakoutRadar.tsx` — age-grouped UI with visual indicators
- `frontend/src/BreakoutBadge.tsx` — add age display to badge

**Changes:**

1. **Replace flat `BROKEN_OUT` section** with age-grouped subsections:
   - 🔥 **Fresh Breakouts (Day 0-1)** — highlighted with accent border
   - 📈 **Early Continuation (Day 2-3)** 
   - ⚠️ **Late Entry Zone (Day 4-5)** — muted styling
   - 💤 **Mature Breakouts (Day 6+)** — collapsed by default

2. **Add "Breakout Age" column** to the radar table:
   - Numeric age + emoji badge
   - Tooltip with full label text

3. **Add "Radar Priority" column** showing the age-weighted MOSI score

4. **`READY_TO_BREAKOUT` section** gets "Coil Age" display:
   - Shows how many days in VCP formation

5. **"🔥 New Today" hero section** at the top:
   - Only shows when there are age=0 breakouts
   - Visually distinct (gradient background, larger text)
   - This is the first thing a trader scans for each morning

**Verification:**
- `npx tsc --noEmit` — 0 errors
- `npm run build` — clean bundle
- Visual check: age badges render correctly in each zone

---

### Phase 4 — STEE Integration + Morning Brief (~30 min)

**Files Modified:**
- `engine_core/swing_execution_engine.py` — age-aware entry filter
- Morning brief skill (if wired) — include age in verdict

**STEE Changes:**
1. In `process_entries()`, after breakout qualification, fetch `breakout_age` for the symbol
2. Apply soft filter:
   - Age 0-2: full position (no change)
   - Age 3-5: log warning, reduce position by 50% (multiply `size_modifier` by 0.5)
   - Age >5: skip entry, log `"Skipping {sym}: mature breakout (Day {age})"`
3. Log age in audit event metadata for post-trade analysis

**Morning Brief Changes:**
1. Include `breakout_age` + `age_label` in the BUY/SKIP/WATCH output
2. Weight the age into the recommendation: Day 0-1 nudges toward BUY, Day 5+ nudges toward WATCH

**Verification:**
- STEE unit test: mock a stock with age=7, verify it's skipped
- STEE unit test: mock a stock with age=1, verify full position
- Regression: all existing STEE behavior unchanged for stocks without age data

---

## Rollback Plan

1. **Schema is additive-only** (`ADD COLUMN IF NOT EXISTS`). Rollback = set column to NULL:
   ```sql
   UPDATE daily_prices SET breakout_age = NULL;
   ```
2. **API changes are backward-compatible** — new fields added, existing fields unchanged.
3. **Frontend gracefully handles `null` age** — existing BreakoutBadge continues to work.
4. **STEE changes are behind age check** — `if breakout_age is not None` guard.

---

## Risk Analysis

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Historical age not populated (only future runs) | Certain | Age=NULL means "no data" — UI shows "—". Backfill optional. |
| Edge case: stock oscillates BROKEN_OUT ↔ CONSOLIDATING daily | Low | Age resets on every transition — correct behavior. |
| Performance: extra column in PERSIST_ROWS writes | Negligible | 1 extra INTEGER per row in existing UPDATE batch. |
| STEE position reduction too aggressive | Medium | Phase 4 uses soft filter (warning + 50%), not hard block. Tunable via constant. |

---

## Out of Scope (Future)

1. **Backfill historical breakout_age** — would require recomputing indicator_engine across full history. Deferred.
2. **Email alerts for Day 0 breakouts** — "New Breakout Alert" push notification. Good follow-up.
3. **Breakout failure tracking** — detect BROKEN_OUT → CONSOLIDATING transitions and log as "Failed Breakout". Useful for STEE exit refinement.
4. **Age-weighted scoring in MRI total_score** — breakout_age could become an 8th scoring condition. Needs backtest validation first.

---

## Commit Plan

| Phase | Commit Message |
|-------|---------------|
| 1 | `feat(indicators): compute breakout_age — tracks days since breakout state transition` |
| 2 | `feat(api): Breakout Radar V2 — age-sorted, priority-scored, grouped by freshness` |
| 3 | `feat(ui): Breakout Radar V2 — age-grouped sections + Fresh Today hero + age badges` |
| 4 | `feat(stee): age-aware entry filter — deprioritize mature breakouts` |

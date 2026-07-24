# CAI V2.0 — Capital Allocation Intelligence: Execution Plan

**Based on:** `docs/24July26CAI_V2_PRD.md`
**Date:** 2026-07-24
**Status:** Proposed

---

## Summary

CAI V2 adds a portfolio management workspace inside the existing MRI app. MRI discovers opportunities; CAI decides what to do with them — buy, add, hold, wait, reduce, rotate, exit. Two review engines (Candidate / Position), a weekly Investment Committee, an immutable Decision Ledger, and a Replay feature.

---

## What Already Exists (no build needed)

| Asset | Location | Notes |
|-------|----------|-------|
| Capital Allocation Score engine | `engine_core/capital_allocation.py` (826 lines) | Eligibility gates, market structure, CAS multipliers, confidence stars |
| Capital allocation config | `config/capital_allocation.yaml` | All thresholds, weights, calibration |
| Portfolio simulation | `engine_core/portfolio_engine.py` | Backtest portfolio simulation |
| Portfolio next-day engine | `engine_core/portfolio_engine_nextday.py` | Next-day execution logic |
| Portfolio risk audit | `engine_core/portfolio_review_engine.py` (453 lines) | Risk classification engine |
| Portfolio API | `api/portfolio.py` (434 lines) | Positions, risk audit endpoints |
| Portfolio review API | `api/portfolio_review.py` | Existing review endpoints |
| DB tables | `client_portfolio`, `swing_trades`, `stock_scores` | Core positions, swing trades, scores |
| Risk Audit frontend page | Registered in `App.tsx` | Already has UI |
| Weekly chart data | `daily_prices` table | OHLCV data available — chart rendering needed |

---

## What Must Be Built

### Phase 1 — Database & Backend Foundation (2–3 days)

| Task | Deliverable | Lines (est.) | Dependencies |
|------|-------------|-------------|--------------|
| 1a. Create CAI DB tables | `engine_core/db.py` migration: `portfolio`, `position`, `position_review`, `committee_report`, `committee_decision`, `decision_ledger` | ~150 | None |
| 1b. Build Portfolio service | `engine_core/cai_portfolio_service.py` — CRUD for portfolio/positions, allocation tracking, tranche management | ~300 | 1a |
| 1c. Build Weekly Chart engine | `engine_core/cai_weekly_chart_engine.py` — OHLCV to weekly candles, swing low detection, structure break detection | ~250 | 1a |
| 1d. Build Position Health engine | `engine_core/cai_position_health.py` — 0-100 score from trend quality, RS, earnings quality, institutional participation, drawdown, structure integrity, allocation risk | ~200 | 1a, 1c |
| 1e. CAI API endpoints | `api/cai.py` — GET /portfolio, GET /portfolio/{id}, POST /review, GET /review/{id}, POST /committee/generate, GET /committee/latest, POST /decision/execute, GET /ledger, GET /replay/{review_id} | ~400 | 1a-1d |
| 1f. Register in API router | Modify `api/main.py` to include CAI router | ~5 | 1e |

### Phase 2 — Core Review Workflows (2–3 days)

| Task | Deliverable | Lines (est.) | Dependencies |
|------|-------------|-------------|--------------|
| 2a. Candidate Review backend | `engine_core/cai_candidate_review.py` — BUY FIRST TRANCHE / WATCH / REJECT logic, integrates MRI score + CAS | ~150 | 1a, 1d |
| 2b. Position Review backend | `engine_core/cai_position_review.py` — ADD / WAIT / HOLD / REDUCE / EXIT / ROTATE logic with cost basis, tranche eligibility, capital allocation checks | ~200 | 1a, 1d |
| 2c. Candidate Review UI | `frontend/src/CaiCandidateReview.tsx` — modal/panel inside STEE, BreakoutRadar, 112Co pages | ~250 | 2a, 1c |
| 2d. Position Review UI | `frontend/src/CaiPositionReview.tsx` — full review page with weekly chart, swing low selection, recommendation output | ~350 | 2b, 1c |
| 2e. Weekly Chart component | `frontend/src/CaiWeeklyChart.tsx` — render weekly OHLCV candlesticks with swing low/structure break overlays | ~250 | 1c |

### Phase 3 — Committee, Ledger & Replay (1–2 days)

| Task | Deliverable | Lines (est.) | Dependencies |
|------|-------------|-------------|--------------|
| 3a. Investment Committee engine | `engine_core/cai_committee.py` — Friday batch: inputs = portfolio + cash + pending reviews + MRI scores + allocation rules, outputs = recommendations per position | ~150 | 1a, 2b |
| 3b. Monday Execution engine | Part of `engine_core/cai_ledger.py` — execution status (Executed / Skipped / Deferred), price storage | ~50 | 3a |
| 3c. Decision Ledger engine | `engine_core/cai_ledger.py` — immutable append-only audit trail, outcome tracking | ~150 | 3a, 3b |
| 3d. Replay engine | `engine_core/cai_replay.py` — reconstruct historical weekly chart + swing low + structure break + recommendation from stored review data | ~100 | 1c, 2b |
| 3e. Committee UI | `frontend/src/CaiCommittee.tsx` — weekly committee report view | ~200 | 3a |
| 3f. Ledger UI | `frontend/src/CaiLedger.tsx` — searchable/filterable decision history | ~150 | 3c |
| 3g. Replay UI | `frontend/src/CaiReplay.tsx` — step-through historical reviews | ~150 | 3d |

### Phase 4 — Navigation & Integration (1–2 days)

| Task | Deliverable | Lines (est.) | Dependencies |
|------|-------------|-------------|--------------|
| 4a. Portfolio Workspace UI | `frontend/src/CaiPortfolioPage.tsx` — holdings with MRI Score, CAI Position Health, Allocation %, Tranche Progress, Review button | ~300 | 1e, 1d |
| 4b. CAI Dashboard (hub) | `frontend/src/CaiDashboard.tsx` — landing page for CAI workspace with summary cards | ~200 | 4a |
| 4c. Sidebar navigation | Modify `frontend/src/App.tsx` — add CAI section with sub-pages under the CAI heading | ~50 | 4b |
| 4d. App.css styles | Add CAI-specific styles (review cards, weekly chart, health badges, committee layout) | ~200 | 4a-4g |
| 4e. Embed Candidate Review in discovery screens | Modify STEE, BreakoutRadar, 112Co pages — add "Candidate Review" button per stock, route to review flow | ~50 | 2c |
| 4f. Embed Position Review in Portfolio | Wire Review button in portfolio table to Position Review page | ~20 | 2d, 4a |

---

## Total Code Volume

| Layer | New Files | New Lines |
|-------|-----------|-----------|
| Backend (Python) | 9 files | ~1,650 |
| Frontend (TSX/TS) | 9 files | ~1,850 |
| Styles (CSS) | 1 file | ~200 |
| Config / wiring | ~3 modifications | ~75 |
| **Total** | **~19 files** | **~3,775 lines** |

---

## Estimated Cost

### Development (one-time)

| Item | Estimate |
|------|----------|
| Engineering hours | 40–70 hours (6–10 days at 7h/day) |
| AI-assisted dev cost | ~$80–$120 (DeepSeek V4: ~200–300 turns at $0.14/M input tokens) |
| **Total one-time cost** | **~$80–$120** (AI tooling only; developer time is the real cost) |

### Ongoing (per month)

| Item | Estimate | Notes |
|------|----------|-------|
| Infrastructure | $0 | Same AWS RDS instance, same Railway/self-hosted compute. No new services. |
| API costs | $0 | No external API calls added. Reuses existing market data in daily_prices. |
| Storage | ~$0.50 | Decision Ledger + reviews add ~5MB/year. Negligible. |
| **Total monthly** | **~$0.50** | |

---

## Timeline

| Phase | Duration | Total |
|-------|----------|-------|
| Phase 1: DB & Backend Foundation | Days 1-3 | 3 days |
| Phase 2: Core Review Workflows | Days 3-5 | 3 days (parallel start with Phase 1 tail) |
| Phase 3: Committee, Ledger & Replay | Days 5-6 | 2 days |
| Phase 4: Navigation & Integration | Days 6-7 | 2 days |
| Buffer / testing | Days 7-10 | 3 days |
| **Total** | **7-10 calendar days** | |

---

## Key Risks

1. **Weekly chart rendering** — No existing candlestick chart component in the frontend. Need a library (recharts does line charts; may need lightweight-charts or similar). Adds ~1 day for integration.
2. **Swing low selection UX** — User selects swing low from a chart. If auto-detection is deferred (PRD lists it as future), the manual click interaction needs careful UX design.
3. **Portfolio data migration** — Existing client_portfolio table has entry price, quantity, highest_price but no tranche tracking or allocation %. May need a migration or bridge.
4. **Candidate Review integration depth** — Embedding in 3 discovery pages (STEE, BreakoutRadar, 112Co) means touching 3 existing components. Low risk but needs careful routing.

---

## Recommended Build Order

```
Day 1-2:  Phase 1a to 1d               (backend foundation, testable in isolation)
Day 3:    Phase 1e to 1f               (API layer, testable with curl/httpx)
Day 3-4:  Phase 2a to 2b               (review engines, testable via API)
Day 4-5:  Phase 2c to 2e               (review UIs + chart component)
Day 5-6:  Phase 3a to 3d               (committee + ledger + replay)
Day 6-7:  Phase 3e to 3g               (committee + ledger + replay UIs)
Day 7-8:  Phase 4a to 4d               (portfolio UI + nav + styles)
Day 8-9:  Phase 4e to 4f               (integration into existing screens)
Day 9-10: Testing, edge cases, deploy
```

---

## Acceptance Checklist (from PRD Section 17)

- [ ] Portfolio visible inside MRI
- [ ] Review generated without screenshots
- [ ] Weekly charts generated from OHLCV
- [ ] Reviews permanently stored
- [ ] Committee generated every Friday
- [ ] Decision Ledger fully auditable
- [ ] Replay reconstructs historical reviews
- [ ] CAI integrated as a dedicated MRI workspace

# Breakout & Ready‑to‑Breakout Implementation – Task Document
**Date:** May 21 2026

## Overview
We will add a deterministic breakout‑identification layer to the MRI platform. It will:
1. Classify each symbol daily as **BROKEN_OUT**, **READY_TO_BREAKOUT**, or **CONSOLIDATING**.
2. Persist the classification in the database.
3. Expose a new API endpoint.
4. Provide a dedicated dashboard page with sortable tables and badge UI.
5. Include documentation and testing to keep the feature maintainable.

---

## Milestones & Task List
| # | Task | Owner | Target date | Status | Acceptance criteria |
|---|------|-------|-------------|--------|----------------------|
| 1 | **Database migration** – add `breakout_state` column to `daily_prices` & `stock_scores`; update `api/schema.py` for auto‑creation. | DB Lead | 2026‑05‑23 | ☐ Not started | Columns exist, default applied to all rows, migration runs cleanly. |
| 2 | **Engine update** – extend `engine_core/indicator_engine.py` to compute price‑range %, volume multiplier, proximity checks; apply breakout formulas and write `breakout_state`. | Core Engine Owner | 2026‑05‑26 | ☐ Not started | Daily run populates `breakout_state` for every row; no NULLs. |
| 3 | **Unit‑test suite** – create `tests/test_breakout_engine.py` covering historical breakout cases (e.g., POLYCAB, HDFCBANK). | QA Lead | 2026‑05‑28 | ☐ Not started | Tests pass on snapshot DB; coverage ≥ 90 %. |
| 4 | **API endpoint** – add `/api/signals/breakouts` returning today’s breakout candidates with supporting fields (`close`, `volume_multiplier`, `proximity`, `mri_score`). | API Owner | 2026‑05‑30 | ☐ Not started | Correct JSON schema; response time < 200 ms. |
| 5 | **Frontend page** – create a new route “Breakout Insights” in `frontend/src/App.tsx`; build `BreakoutDashboard.tsx` that consumes the new API, shows two tables (Active / Ready), badge styling, sortable columns, filter toggle. | Frontend Lead | 2026‑06‑02 | ☐ Not started | Badges display, filter works, UI matches design system. |
| 6 | **Documentation** – add section to `docs/FEATURE_BREAKOUT.md` describing the classification logic, DB schema, API contract, and UI usage. Update `Progress.md` to reflect the new milestone. | Docs Owner | 2026‑06‑03 | ☐ Not started | Docs are merged, searchable, and referenced from the task list. |
| 7 | **End‑to‑end verification** – run full `pipeline_cloud.sh`, verify DB values, hit the new API, and view the dashboard page. | Integration Lead | 2026‑06‑04 | ☐ Not started | Engine → DB → API → UI all show consistent breakout states; no errors in logs. |
| 8 | **Release & deployment** – merge to `main`, rebuild Docker image, restart FastAPI, and confirm breakout page appears in production after the next pipeline run. | Release Manager | 2026‑06‑06 | ☐ Not started | Deployment succeeds; production dashboard shows breakout data within 24 h. |

---

## Visual Mockup (concept only)
```
+-----------------------------------------------------+
| Breakout Insights (Dashboard)                       |
+-----------------------------------------------------+
| [All]  [Active]  [Ready]                           |
+-----------------------------------------------------+
| **Active Breakouts**                               |
| Symbol | Close | Vol × Avg | Proximity | MRI Score |
| --------------------------------------------------- |
| POLYCAB | 7,120.5 | 1.45 | 0 % | 85 |
| ...                                           |
+-----------------------------------------------------+
| **Ready‑to‑Breakout**                               |
| Symbol | Close | Vol × Avg | Proximity | MRI Score |
| --------------------------------------------------- |
| ABCDEF | 1,254.3 | 0.78 | 2 % | 72 |
| ...                                           |
+-----------------------------------------------------+
```

---

## Next Steps
1. Open a PR for the DB migration (Task 1).<br>
2. Once merged, start work on the engine update (Task 2).<br>
3. Keep this document up‑to‑date as tasks move forward.

---

*All tasks are incremental, testable, and respect the existing architecture outlined in `AGENTS.md`. Any future design changes will be logged in `Decisions.md`.*

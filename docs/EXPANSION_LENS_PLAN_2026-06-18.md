# Expansion Lens — Execution Plan (Manual, 149-Universe Scope)

**Date:** 2026-06-18
**Owner:** Immanuel Santosh
**Status:** Draft — ready for execution
**Predecessor:** `docs/AAE_INTEGRATION_PLAN_2026-06-17.md`

---

## Goal

Ship the **Expansion Lens** as a reachable, manually-refreshed report screen + email tool for the 149-symbol universe already scored in `perx_pe_scores`. No auto-scraping, no daily cron, no PERX-integration.

## Constraints

1. **Manual only.** No transcript discovery / ingestion / cron job. Data is only as fresh as the last `prime_missing_only.py` + `run_narrative_tracer_universe.py` + `--persist` run.
2. **149-symbol scope.** Search/autocomplete and Top 10 only surface symbols with rows in `perx_pe_scores` (currently 149). Broader `stock_sectors` universe search is out of scope.
3. **Standalone surface.** No integration into `engine_perx/scoring.py:compute_perx_score`. The existing `/perx/[symbol]` report is unchanged.
4. **No schema changes.** No new tables, no new columns. Reuse existing `perx_pe_scores`, `perx_pe_signals`, `management_narrative_timeline`, `stock_sectors`, `aae_transcripts`, `email_log`.
5. **No new dependencies.** `boto3` already in `requirements.txt`. Use existing FastAPI / psycopg2 / React.
6. **Internal naming unchanged.** Route prefix `/api/pe-expansion/`, function names (`build_pe_expansion_report`, `pe_expansion_router`), DB tables, page state key (`'peexpansion'`), and `email_log.email_type='pe_expansion_report'` stay as-is.
7. **Existing tests stay green.** The 77/77 regression suite from June 17 must still pass.

## Chunks (4 ordered units)

### Chunk 1 — Backend endpoints

**Scope:**

- `api/pe_expansion.py` — add 2 endpoints (file already exists with the report-builder + JSON/email/preview routes from yesterday):
  - `GET /api/pe-expansion/suggest?q=POL&limit=10` — autocomplete from `perx_pe_scores JOIN stock_sectors` filtered by `q ILIKE` on `symbol` OR `company_name`. Empty `q` returns top 10 by `pe_score DESC`.
  - `GET /api/pe-expansion/top10` — top 10 from `perx_pe_scores` (ORDER BY `pe_score DESC` LIMIT 10) + `as_of` timestamp = `MAX(updated_at)`.
- Verify `perx_pe_scores.updated_at` exists; if not, fall back to `pg_stat` or `MAX(date)` equivalent.

**Depends On:** nothing

**Accept When:**

- `curl localhost:8000/api/pe-expansion/suggest?q=POL` → JSON with POLYCAB + ≥1 row
- `curl localhost:8000/api/pe-expansion/top10` → JSON with 10 rows + `as_of` ISO string
- Both endpoints return 200 OK with valid JSON
- `ast.parse` clean on `api/pe_expansion.py`

**Open Questions:** none

### Chunk 2 — Frontend: search box + Top 10 panel

**Scope:**

- `frontend/src/PeExpansionReport.tsx` — add above the existing report tree:
  - Search input (debounced 200ms) wired to `/api/pe-expansion/suggest` with a clickable autocomplete dropdown
  - Selecting an autocomplete row OR pressing Enter → updates internal `symbol` state → existing `useEffect` re-fetches the report
  - Compact Top 10 panel (sourced from `/api/pe-expansion/top10`) — each row clickable, also sets `symbol` and re-fetches
  - Footer line under Top 10: `Universe: {total} symbols · Last persist: {as_of} IST · To refresh: python -m engine_perx.pe_signals --persist`
- Stale disclosure: small grey text under the company name showing `coverage.n_quarter_span` and the latest promise quarter
- All 6 existing report sections + email input/Send button stay unchanged

**Depends On:** Chunk 1

**Accept When:**

- Typing "POL" in the search box surfaces POLYCAB in the dropdown
- Clicking POLYCAB (either from dropdown or Top 10) loads the full report (header, drivers, breakdown, primary, secondary, footer)
- The "To refresh" hint is visible under Top 10
- `npx tsc --noEmit` returns 0 errors
- Email Send button still works (regression)

**Open Questions:** none

### Chunk 3 — Renames + nav links (parallelizable with Chunks 1 & 2)

**Scope:**

- `frontend/src/App.tsx`:
  - Sidebar: insert `<button className="nav-link">📈 Expansion Lens</button>` after PERX button (line ~2676)
  - Mobile nav: insert `<button>📈</button>` with `title="Expansion Lens"` after PERX icon (line ~2748)
- `frontend/src/PeExpansionReport.tsx` line 164: `"MRI · PE Expansion Report"` → `"MRI · Expansion Lens"`
- `api/pe_expansion.py`:
  - L78: `"MRI · PE Expansion Report"` → `"MRI · Expansion Lens"`
  - L122: `"Top PE Expansion Drivers"` → `"Top Expansion Drivers"`
  - L270: `"MRI PE Expansion engine"` → `"MRI Expansion Lens engine"`
  - L281: `<title>PE Expansion Report — ...` → `<title>Expansion Lens — ...`
  - L305: `f"PE Expansion Report — ..."` → `f"Expansion Lens — ..."`
  - L357: `f"PE Expansion — ..."` → `f"Expansion Lens — ..."`

**Depends On:** nothing

**Accept When:**

- Sidebar shows "📈 Expansion Lens" between PERX and AAE Console
- Mobile nav shows 📈 between 🏛️ and 🧬
- Page header reads "MRI · Expansion Lens"
- Email HTML for POLYCAB contains `"MRI · Expansion Lens"` and `"Expansion Lens — Polycab India Limited"`
- Email HTML contains ZERO occurrences of `"PE Expansion Report"` or `"Top PE Expansion Drivers"`
- `npx tsc --noEmit` returns 0 errors
- `ast.parse` clean on `api/pe_expansion.py`

**Open Questions:** none

### Chunk 4 — Cleanup + verify

**Scope:**

- `engine_perx/pe_signals.py` lines 815–820: delete the duplicate stub fragment (`# ── Report builder ... ──` comment + redundant `from engine_perx.pe_dictionary import PE_DICTIONARY as _PE_DICT`)
- Full verification pass (see Verification Strategy)

**Depends On:** Chunks 1, 2, 3

**Accept When:**

- `pe_signals.py` is 815 lines (was 820)
- All verifications in the strategy below pass

**Open Questions:** none

## Verification Strategy

| Check | Command | Expected |
|---|---|---|
| Python parse | `python -c "import ast; ast.parse(open('api/pe_expansion.py').read()); ast.parse(open('engine_perx/pe_signals.py').read())"` | exit 0 |
| TypeScript compile | `cd frontend && npx tsc --noEmit` | "No errors found" |
| Regression tests | `pytest` (in venv) | 77/77 pass (no new tests in this plan) |
| Suggest endpoint | `curl localhost:8000/api/pe-expansion/suggest?q=POL` | JSON with POLYCAB |
| Top 10 endpoint | `curl localhost:8000/api/pe-expansion/top10` | JSON with 10 rows + `as_of` |
| JSON report | `curl localhost:8000/api/pe-expansion/POLYCAB` | Full report dict, unchanged |
| Email HTML | `curl localhost:8000/api/pe-expansion/email/preview/POLYCAB` | HTML containing "MRI · Expansion Lens", ZERO occurrences of "PE Expansion Report" |
| Stub removed | `wc -l engine_perx/pe_signals.py` | 815 (was 820) |

## Decision Log

| # | Decision | Rationale |
|---|---|---|
| 1 | Keep route prefix `/api/pe-expansion/` and function names | Internal naming is stable; renaming risks breaking callers and `email_log.email_type` audit trail |
| 2 | `email_log.email_type` stays `'pe_expansion_report'` | Existing dashboard queries filter on this value; renaming silently breaks them |
| 3 | **No** "Refresh ranks" button in UI | User directive: manual only. CLI command shown in Top 10 footer instead |
| 4 | Top 10 footer shows CLI command rather than auto-running | User directive: manual. Make the path obvious, not invisible automation |
| 5 | Search scope = 149 symbols in `perx_pe_scores` | User directive: "for the 149 scripts alone". Broader universe search would suggest coverage that doesn't exist |
| 6 | Stale threshold = show `as_of` + max promise quarter, no alert banner | User knows the data is manual. Show timestamps, don't nag |
| 7 | Nav label = "📈 Expansion Lens" | Selected by user from {Re-Rating Radar, Expansion Lens, Promise Tracker, Forward Rerating} |
| 8 | Chunks 1 & 3 parallelizable | Backend and frontend-nav don't share dependencies |
| 9 | Plan written before code (this doc) | User directive: "before that make an execution plan and add it to docs with date" |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `perx_pe_scores.updated_at` column may not exist | Low — added yesterday during persist | Verify column exists during Chunk 1; fall back to `MAX(generated_at)` or `now() - last_persist` if missing |
| BSE screener.in rate-limits during future bulk runs | Medium — out of scope here | Out of scope; only reuses already-fetched transcripts |
| 149-symbol Top 10 doesn't include a symbol user just typed | Expected — that's the whole "stale" point | Top 10 footer discloses manual refresh path |
| Nav link proliferation | Low — 13 sidebar items (was 12) | Acceptable; can revisit grouping later |
| Email Log row count growth from test sends | Low — no new test code added | N/A |

## Out of Scope (deferred)

- Auto-discovery / BSE-NSE scraping → explicit user deferral ("keep it manual for now")
- Integration into `compute_perx_score` → explicit user deferral ("we want the new report only")
- Bulk email digest → not requested
- `n_quarter_span: 1` oddity for POLYCAB → cosmetic, not blocking
- Coverage backfill for the ~43 universe symbols without promise rows → not part of this plan
- PERX PRD vocabulary rename (still says "PE Expansion") → cosmetic, breaks nothing

---

## Sign-off

Ready to execute. Estimated total effort: ~55 min (Chunks 1+2 sequential, Chunk 3 parallelizable, Chunk 4 = verification).

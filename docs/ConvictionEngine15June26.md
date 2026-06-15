# ConvictionEngine — Execution Plan

**Date:** 2026-06-15
**Branch:** `feature/conviction-engine`
**Owner:** Lead AI Engineer
**Status:** DRAFT — awaiting user approval before execution

---

## 1. Goal

Systematize **management integrity tracking** across the two lists the user actively trades:

1. **Digital Twin** — user's actual portfolio (`client_external_holdings`)
2. **112 Co Universe** — PE-expansion breakout watchlist (`universe_112co`)

For every name in either list, ConvictionEngine must:

- Ingest **≥ 2 quarters** of transcripts / concall PPTs
- Extract forward-looking management statements (already built in `engine_guidance/`)
- Verify each promise against actual quarterly results
- Persist **per-quarter observation rows** in the DB
- Surface a **Conviction verdict** per company: `ADD ZONE` / `HOLD ZONE` / `REDUCE ZONE` / `THESIS BROKEN`
- Auto-update **every quarter** and flag when management is **lagging** (consecutive miss-quarters)

---

## 2. What Already Exists (no rebuild)

| Asset | File | Status |
|-------|------|--------|
| `management_guidance` table | `api/schema.py → ensure_guidance_tables()` | ✅ live |
| `guidance_verification` table | same | ✅ live |
| `management_credibility_scores` table | same | ✅ live |
| `user_thesis` table | same | ✅ live |
| Concall PDF discovery (Screener + NSE fallback) | `engine_guidance/bse_concall_finder.py` | ✅ live (Decision 095) |
| GPT-4o-mini forward-statement extractor | `engine_guidance/guidance_extractor.py` | ✅ live |
| Verifier (promise vs financials) | `engine_guidance/guidance_verifier.py` | ✅ live |
| Credibility scorer with trend | `engine_guidance/credibility_scorer.py` | ✅ live |
| Prime-all for watchlist + holdings | `scripts/prime_all_guidance.py` | ✅ live (Decision 096) |
| Quarterly verification job | `scripts/run_quarterly_guidance_check.py` | ✅ scheduled in `pipeline_cloud.sh` |
| API: dashboard, report, email, scan, thesis, prime | `api/guidance.py` | ✅ live (modified today) |
| Demo runner with conviction labels | `scripts/guidance_check_demo.py` | ✅ live |
| React UI `GuidanceCheck.tsx` | `frontend/src/` | ✅ live |

**Coverage gap**: `universe_112co` is **not** in the prime-all loop and **not** in the quarterly verifier. That's the only structural gap.

---

## 3. Scope Boundary — IN

- Ingest the **112 Co Universe** (`universe_112co` where `is_active=true`)
- Extend credibility schema with **lag metrics** (consecutive miss-quarters, lag-score)
- Build a unified **`/api/guidance/conviction`** endpoint (Digital Twin ∪ 112Co)
- Add a **`ConvictionEngine.tsx`** dashboard ranked by verdict
- Extend quarterly job to detect **lag flips** and emit alerts

## 4. Scope Boundary — OUT

- Building new LLM extraction (reuse existing `guidance_extractor`)
- New PDF source beyond Screener.in + NSE fallback
- Multi-language transcripts (English only, Indian concalls)
- Cost: estimated **< $0.20/quarter** for 112 + Digital Twin combined (per existing cost model: $0.00015/transcript × ~250 transcripts × 4 quarters/yr)

---

## 5. Phased Plan

### Phase 1 — Coverage Parity for 112Co *(smallest first slice)*

**Why first**: zero schema/code risk; one config change unlocks the entire 112 list.

| Step | File | Change |
|------|------|--------|
| 1.1 | `scripts/prime_all_guidance.py` | Add `cur.execute("SELECT DISTINCT UPPER(symbol) FROM universe_112co WHERE is_active=true")` to `get_all_symbols()`. Log source breakdown (watchlist / holdings / 112co). |
| 1.2 | `scripts/run_quarterly_guidance_check.py` | Same change to symbol-discovery so quarterly verification iterates the 112 list. |
| 1.3 | shell | Run `python3 scripts/prime_all_guidance.py --limit 10 --dry-run` then full run with rate-limit (1 stock/sec) to stay under LLM RPM. |

**Verify (P1 acceptance signal)**:
- `bash -c "python3 -c \"from engine_core.db import get_connection; c=get_connection(); cur=c.cursor(); cur.execute('SELECT COUNT(DISTINCT symbol) FROM management_guidance WHERE symbol IN (SELECT symbol FROM universe_112co WHERE is_active=true)'); print(cur.fetchone()); c.close()\""`
- Expected: row count grows toward 100+ over the priming run

**Risk**: Screener.in 404s on some 112 names → NSE fallback (Decision 095) already covers this. If still missing, log and continue — never block the pipeline.

---

### Phase 2 — Lag Metrics on the Credibility Table

**Why second**: the existing `trend` column (`IMPROVING/STABLE/DETERIORATING/INSUFFICIENT_DATA`) is computed but never stored as a quarterly time-series. Lag detection needs it.

| Step | File | Change |
|------|------|--------|
| 2.1 | `api/schema.py → ensure_guidance_tables()` | `ALTER TABLE management_credibility_scores ADD COLUMN IF NOT EXISTS consecutive_miss_quarters INT DEFAULT 0, ADD COLUMN IF NOT EXISTS lag_score NUMERIC(5,2) DEFAULT 0, ADD COLUMN IF NOT EXISTS last_verdict_flip DATE` (idempotent) |
| 2.2 | `engine_guidance/credibility_scorer.py → compute_score()` | Compute `consecutive_miss_quarters` by walking `guidance_verification` rows in `checked_fiscal_year, checked_fiscal_quarter` order, counting MISSED from the most recent verified quarter backwards until an ACHIEVED/PARTIAL appears. Compute `lag_score` = `(consecutive_miss_quarters / total_verified_quarters) * 100`. Detect verdict flips and stamp `last_verdict_flip`. |
| 2.3 | `api/guidance.py → _build_report_payload()` | Surface new fields in JSON: `lag_count`, `lag_score`, `verdict_flip_date`. |

**Verify (P1 acceptance signal)**:
- `python3 -m pytest tests/test_credibility_scorer_lag.py -v` (new test: mock 4 quarters with 2 recent MISSED → assert `consecutive_miss_quarters=2`)
- `bash -c "python3 -c \"from engine_core.db import get_connection; c=get_connection(); cur=c.cursor(); cur.execute(\\\"SELECT column_name FROM information_schema.columns WHERE table_name='management_credibility_scores'\\\"); print([r[0] for r in cur.fetchall()])\""` → must include `consecutive_miss_quarters`, `lag_score`, `last_verdict_flip`

**Risk**: schema migration on a table with rows. Mitigated by `IF NOT EXISTS` and the existing RDS-protection rules (Decision 027).

---

### Phase 3 — Unified Conviction Endpoint + React Dashboard

| Step | File | Change |
|------|------|--------|
| 3.1 | `api/guidance.py` | New `GET /api/guidance/conviction?source=digital_twin\|112co\|all&verdict=any&limit=50`. Union `client_external_holdings` + `universe_112co` symbols, left-join `management_credibility_scores`. Returns sorted by `accuracy_pct ASC, lag_score DESC` (worst first by default). |
| 3.2 | `api/main.py` | Already includes guidance router — no change. |
| 3.3 | `frontend/src/ConvictionEngine.tsx` | New single-screen dashboard. Columns: Symbol, Source, Accuracy %, Trend, Lag Score, Verdict (color-coded chip), Last Updated. Source filter chips (Digital Twin / 112 Co / All). Click row → existing `/guidance/{symbol}/report` modal. |
| 3.4 | `frontend/src/App.tsx` | Sidebar entry "🧠 Conviction Engine" between GuidanceCheck and Risk Audit. |

**Verify (P1 acceptance signal)**:
- `curl -s http://localhost:8000/api/guidance/conviction?source=all | python3 -m json.tool | head -40` returns ranked JSON
- Manual: open dashboard, filter 112 Co, see INFY row with 63% accuracy + 🟡 Hold Zone verdict (matches today's demo output)

**Risk**: Frontend coupling. Mitigated by reusing existing chip/card primitives from `GuidanceCheck.tsx`.

---

### Phase 4 — Quarterly Lag Alerting

| Step | File | Change |
|------|------|--------|
| 4.1 | `scripts/run_quarterly_guidance_check.py` | After scoring, query `WHERE last_verdict_flip >= NOW() - INTERVAL '7 days'` and emit structured log lines (one per flip). |
| 4.2 | `engine_core/email_service.py` | New helper `build_conviction_alert_email_html(flips: list[dict])`. Subject: "🚨 Conviction Alert: N management teams just flipped verdict". |
| 4.3 | `scripts/pipeline_cloud.sh` | After `run_quarterly_guidance_check.py`, add: `python3 scripts/send_conviction_alerts.py` (new 1-file script that fetches flips and emails opted-in clients). |
| 4.4 | `scripts/send_conviction_alerts.py` | New file. Reads flips from DB, fetches `client_alert_preferences` (new tiny table: `client_id, conviction_alerts_enabled BOOLEAN`), sends via existing `email_service.send_email_custom`. |

**Verify (P1 acceptance signal)**:
- `python3 scripts/run_quarterly_guidance_check.py --dry-run` returns flips list with shape `[{symbol, old_verdict, new_verdict, lag_count, source}]`
- `python3 scripts/send_conviction_alerts.py --to test@example.com --preview` produces HTML in `outputs/conviction_alert_preview.html` and exits 0
- Manual: trigger for INFY (current 63% hold → if next quarter slips, alert fires)

**Risk**: Email spam if every minor wobble triggers. Mitigated by only alerting on `verdict_flip` (crossing a zone boundary), not raw accuracy changes.

---

## 6. Order-of-Operations Gates

**P1 (verifiable success per phase)**: each phase above has a concrete `Verify` block with a deterministic check (pytest, psql, curl, file-exists).

**P2 (each phase feeds the next)**:
- Phase 1 produces populated `management_guidance` rows for the 112 list
- Phase 2 reads those rows to compute lag metrics
- Phase 3 reads lag metrics to render the dashboard
- Phase 4 reads lag-metric transitions to fire alerts
**Pipeline is sound. Parallel-group not needed — strict linear dependency.**

**P3 (ship evidence checklist)**:
- [ ] `universe_112co` symbols present in `management_guidance` (≥100 rows)
- [ ] `management_credibility_scores` has the 3 new columns populated
- [ ] `curl /api/guidance/conviction?source=all` returns ≥50 rows
- [ ] `ConvictionEngine.tsx` renders with verdict chips
- [ ] `run_quarterly_guidance_check.py` produces flip log entries
- [ ] `send_conviction_alerts.py` produces preview HTML without sending real email
- [ ] `Decisions.md` Decision 097 added
- [ ] `Progress.md` session entry added
- [ ] Branch `feature/conviction-engine` pushed, PR opened

---

## 7. Cost & Runtime Estimate

| Operation | Count | Cost | Wall Time |
|-----------|-------|------|-----------|
| Prime 112 list (concall discovery + GPT extraction) | ~100 stocks × ~3 transcripts each | ~$0.05 | ~15 min |
| Phase 1 verification pass | 100 stocks | ~$0.02 | ~5 min |
| Quarterly rerun (steady state) | 250 stocks × 1 new transcript | ~$0.04 | ~10 min |
| Lag-alert emails (steady state) | < 10/quarter | < $0.01 | < 1 min |

**Total one-time priming**: ~$0.07, ~20 min.
**Steady-state quarterly cost**: ~$0.05.

---

## 8. Rollback Plan

All changes are additive:
- New columns use `ADD COLUMN IF NOT EXISTS`
- New endpoint is additive (`/api/guidance/conviction`)
- New frontend route is additive (new sidebar entry, no removal)
- Prime-all changes just add a source — removing the 112 line reverts
- Quarterly alerts can be disabled via `client_alert_preferences` row

**Single command rollback**: `git revert <merge-sha>` on `main`.

---

## 9. Open Questions for User (non-blocking — defaults proposed)

1. **Cost gate**: cap per-quarter LLM spend at $0.50 with a kill-switch? *Default: yes, kill at $0.50.*
2. **Email opt-in**: should we auto-enable lag alerts for existing users, or default-off with a settings toggle? *Default: default-off, explicit opt-in via `user_thesis`-style preference.*
3. **Conviction threshold tuning**: current zones are 75/60/40 % accuracy. Tweak? *Default: keep current.*
4. **Lag-alert cadence**: only on verdict flip, or weekly digest? *Default: flip-only.*

---

## 10. Execution Checklist (post-approval)

```
[ ] git checkout -b feature/conviction-engine
[ ] Phase 1.1: edit scripts/prime_all_guidance.py
[ ] Phase 1.2: edit scripts/run_quarterly_guidance_check.py
[ ] Phase 1.3: run priming for 112 list
[ ] Phase 2.1: extend ensure_guidance_tables()
[ ] Phase 2.2: extend credibility_scorer.py
[ ] Phase 2.3: surface new fields in api/guidance.py
[ ] Phase 2: add tests/test_credibility_scorer_lag.py
[ ] Phase 3.1: add /api/guidance/conviction endpoint
[ ] Phase 3.3: write ConvictionEngine.tsx
[ ] Phase 3.4: wire sidebar in App.tsx
[ ] Phase 4.1-4.4: alerting pipeline
[ ] Decisions.md → Decision 097
[ ] Progress.md → session entry
[ ] git push + open PR
```

---

**END OF PLAN — Awaiting user approval before execution.**

# PRDE Step-by-Step Implementation Checklist

## Product

PRDE - PE Re-Rating Discovery Engine

## Current Milestone

Build PRDE as a fundamentals intelligence layer inside the existing MRI monolith.

The immediate goal is not to generate AI reports yet. The immediate goal is to create a reliable fundamentals data foundation, then deterministic features, then agent scoring.

## Guiding Rule

Do not add LLM agents until the financial data import path is repeatable and validated.

## Phase 0 - Planning and Architecture

- [x] Review PRDE PRD against existing MRI architecture.
- [x] Create infrastructure reuse plan.
- [x] Decide PRDE stays inside the existing FastAPI/Railway/Neon monolith.
- [x] Log architecture decision.

Artifacts:

- `docs/PRDE_INFRASTRUCTURE_PLAN.md`
- `Decisions.md` - Decision 084

Done criteria:

- Clear answer exists for what MRI infra PRDE reuses.
- Clear answer exists for what PRDE still needs.

## Phase 1 - Data Foundation

### 1.1 Schema

- [x] Add PRDE schema bootstrap tables to `api/schema.py`.
- [x] Add `prde_companies`.
- [x] Add `prde_financials_annual`.
- [x] Add `prde_ratios_annual`.
- [x] Add `prde_feature_snapshots`.
- [x] Add `prde_agent_scores`.
- [x] Add `prde_final_scores`.
- [x] Add `prde_report_events`.
- [x] Add `prde_jobs`.
- [x] Add indexes for company/year lookups and final score ranking.

Done criteria:

- Schema is idempotent.
- Tables are under `public.prde_*`.
- Financial rows are unique per company/year.
- Feature and score outputs are traceable.

### 1.2 CSV Import Contract

- [x] Document required CSV columns.
- [x] Document optional valuation and company metadata columns.
- [x] Document accepted number formats.
- [x] Document validation behavior.

Artifact:

- `docs/PRDE_CSV_IMPORT_CONTRACT.md`

Done criteria:

- A user can create a compatible CSV without reading the importer code.

### 1.3 Import Script

- [x] Create `scripts/import_prde_financials.py`.
- [x] Add CSV validation.
- [x] Add `--dry-run` support.
- [x] Add company upserts.
- [x] Add annual financial upserts.
- [x] Add annual ratio upserts.
- [x] Add quality warnings for missing ratios and short company histories.
- [x] Keep DB dependencies lazy so `--help` and dry-run validation stay lightweight.
- [ ] Run dry-run against a real 10-20 company seed CSV.
- [ ] Import seed CSV into configured database.
- [ ] Verify row counts in `prde_companies`, `prde_financials_annual`, and `prde_ratios_annual`.
- [x] Add a blank CSV template for real seed data collection.
- [x] Add a PRDE import verification script.

Commands:

```bash
mkdir -p data
cp docs/prde_financials_template.csv data/prde_financials_seed.csv
python scripts/import_prde_financials.py path/to/prde_financials.csv --dry-run
python scripts/import_prde_financials.py path/to/prde_financials.csv
python scripts/verify_prde_import.py --min-companies 10 --min-years 5
```

Done criteria:

- Dry-run reports clean summary.
- Import is repeatable.
- Re-running the same CSV does not create duplicate company/year rows.

## Phase 2 - Deterministic Feature Engine

- [x] Create `engine_core/prde_feature_engine.py`.
- [x] Load annual financials and ratios by company.
- [x] Compute revenue CAGR.
- [x] Compute EBITDA CAGR.
- [x] Compute PAT CAGR.
- [x] Compute EBITDA growth versus revenue growth.
- [x] Compute PAT growth versus revenue growth.
- [x] Compute EBITDA margin trend.
- [x] Compute PAT margin trend.
- [x] Compute ROCE trend.
- [x] Compute asset turnover trend.
- [x] Compute capex intensity trend.
- [x] Compute employee cost percentage trend.
- [x] Compute debt-equity risk features.
- [x] Generate structured feature JSON per company.
- [x] Hash feature JSON for reproducibility.
- [x] Persist feature JSON to `prde_feature_snapshots`.
- [x] Add CLI entrypoint for feature generation.
- [ ] Run feature engine dry-run against imported seed data.
- [ ] Persist feature snapshots for imported seed data.
- [ ] Verify repeated runs reuse the same feature hash for unchanged data.

Proposed command:

```bash
python engine_core/prde_feature_engine.py --limit 20 --dry-run
python engine_core/prde_feature_engine.py --limit 20
```

Done criteria:

- Same input rows produce same feature hash.
- Feature snapshot stores enough data to reproduce agent scoring later.
- Companies with insufficient data are skipped with clear reason.

## Phase 3 - Deterministic PRDE Scoring Baseline

This phase comes before LLM agents. It gives us a baseline ranking from computed numbers alone.

- [ ] Create `engine_core/prde_scoring_engine.py`.
- [ ] Implement operating leverage numeric score.
- [ ] Implement revenue growth numeric score.
- [ ] Implement margin expansion numeric score.
- [ ] Implement ROCE numeric score.
- [ ] Implement predictability numeric score.
- [ ] Implement valuation gap numeric score.
- [ ] Implement risk penalty.
- [ ] Compute weighted total score.
- [ ] Classify:
  - Strong Candidate
  - Emerging Candidate
  - Watchlist
  - Avoid
- [ ] Persist baseline results to `prde_final_scores`.
- [ ] Join latest MRI trend score and market regime as timing overlay.

Done criteria:

- 10-20 company seed universe can be ranked without LLM calls.
- Each score component is inspectable.
- Final score is reproducible from feature snapshot.

## Phase 4 - LLM Agent Layer

- [ ] Create `engine_core/llm_client.py`.
- [ ] Add env vars:
  - `OPENAI_API_KEY`
  - `PRDE_LLM_MODEL`
  - `PRDE_LLM_MAX_CONCURRENCY`
  - `PRDE_LLM_TIMEOUT_SECONDS`
  - `PRDE_LLM_DAILY_BUDGET`
- [ ] Create `engine_core/prde_agent_runner.py`.
- [ ] Add prompt registry.
- [ ] Add strict JSON response schema.
- [ ] Add malformed-output retry.
- [ ] Cache agent outputs by `feature_snapshot_id`.
- [ ] Store outputs in `prde_agent_scores`.
- [ ] Start with MVP agents:
  - Operating Leverage
  - Revenue Acceleration
  - Margin Expansion
  - ROCE
  - Predictability
  - Valuation Gap
  - Risk
  - Master Decision
- [ ] Defer TAM, Industry Tailwind, and Integration until reliable external narrative data exists.

Done criteria:

- A 10-company run completes without manual intervention.
- A bad LLM response does not kill the whole run.
- Every agent output has score, confidence, reasoning, and flags.

## Phase 5 - Report Generator

- [ ] Create `engine_core/prde_report_generator.py`.
- [ ] Generate JSON report first.
- [ ] Include summary.
- [ ] Include key drivers.
- [ ] Include triggers.
- [ ] Include risks.
- [ ] Include valuation gap explanation.
- [ ] Include MRI timing overlay.
- [ ] Include final verdict.
- [ ] Include compliance disclaimer language.
- [ ] Persist report JSON in `prde_final_scores.report`.

Done criteria:

- Every Strong/Emerging candidate has a complete report.
- Report cites computed feature values and agent outputs.
- Report avoids direct buy/sell instruction wording.

## Phase 6 - API Layer

- [ ] Create `api/prde.py`.
- [ ] Register router in `api/main.py`.
- [ ] Add `GET /api/prde/candidates`.
- [ ] Add `GET /api/prde/companies/{symbol}`.
- [ ] Add admin-only `POST /api/prde/scan`.
- [ ] Add admin-only `GET /api/admin/prde/jobs`.
- [ ] Add admin-only `GET /api/admin/prde/failures`.

Done criteria:

- Candidate list can be fetched from frontend.
- Company report can be fetched by symbol.
- Admin can inspect run status.

## Phase 7 - Scheduler and Email

- [ ] Create `scripts/run_prde_pipeline.py`.
- [ ] Add job row creation in `prde_jobs`.
- [ ] Run import or data refresh step.
- [ ] Run feature engine.
- [ ] Run scoring engine.
- [ ] Run agent layer only for changed feature snapshots.
- [ ] Generate reports.
- [ ] Add `send_prde_report_emails()` to `engine_core/email_service.py`.
- [ ] Log email events in `email_log`.
- [ ] Add 3-day scheduler after manual runs are stable.

Done criteria:

- PRDE run is incremental.
- Unchanged companies do not trigger duplicate LLM calls.
- Email sends only after reports are complete.
- Failures are visible in `prde_jobs` and audit logs.

## Phase 8 - Admin and User UI

- [ ] Add PRDE candidate table to dashboard.
- [ ] Add company report detail view.
- [ ] Add admin run status view.
- [ ] Add failed/skipped company list.
- [ ] Add confidence warnings.

Done criteria:

- User can read final PRDE report without charts or manual interpretation.
- Admin can diagnose stale/missing PRDE outputs.

## Next Session Start Here

Start with Phase 1.3 remaining items:

1. Create a small 10-20 company CSV using `docs/PRDE_CSV_IMPORT_CONTRACT.md`.
2. Run:

```bash
python scripts/import_prde_financials.py path/to/prde_financials.csv --dry-run
```

3. Fix any data formatting issues.
4. Import into the configured database:

```bash
python scripts/import_prde_financials.py path/to/prde_financials.csv
```

5. Verify row counts.
6. Then begin Phase 2: `engine_core/prde_feature_engine.py`.

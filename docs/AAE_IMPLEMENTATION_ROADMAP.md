# AAE Implementation Roadmap

## Current Position

AAE is the long-term product vision. The current active milestone is still PRDE data foundation and deterministic feature generation.

Relationship:

- MRI = existing technical/regime/signal platform.
- PRDE = financial fingerprint and re-rating fundamentals layer.
- AAE = full event-driven multi-agent research platform built on MRI + PRDE.

## Milestone 0 - PRDE Financial Foundation

Status: In progress.

Completed:

- PRDE schema bootstrap added to `api/schema.py`.
- CSV import contract created.
- Blank seed CSV template created.
- Import script created.
- Import verifier created.
- Deterministic feature engine created.

Remaining:

- Build real 10-20 company seed CSV.
- Dry-run validate CSV.
- Import into database.
- Re-run import to prove idempotency.
- Verify row counts and required fields.
- Generate feature snapshots.
- Confirm unchanged data produces stable feature hashes.

Stop rule:

- Do not build LLM agents until this milestone passes.

## Milestone 1 - Deterministic Financial Fingerprint Scoring

Purpose:

- Convert PRDE feature snapshots into transparent numeric scores before adding LLM interpretation.

Deliverables:

- `engine_core/prde_scoring_engine.py`
- Master Investor Checklist scoring.
- Operating leverage classification.
- Capital efficiency score.
- Margin expansion score.
- Growth quality score.
- Valuation gap score.
- Risk penalty.
- MRI trend/regime overlay.
- Persistence into `prde_final_scores`.

Done criteria:

- Seed universe can be ranked without LLM calls.
- Each score component is inspectable.
- Re-running unchanged input produces unchanged output.

## Milestone 2 - AAE Event and Document Foundation

Purpose:

- Introduce event-driven inputs without yet relying on agents for final conclusions.

Deliverables:

- Document metadata schema.
- Event object schema.
- Manual document ingestion script.
- Source evidence storage.
- Event-to-company mapping.

Potential tables:

- `aae_documents`
- `aae_document_chunks`
- `aae_events`
- `aae_event_evidence`

Done criteria:

- A filing or presentation can be ingested and linked to one or more companies.
- Extracted events retain source references.
- Events can be replayed or audited.

## Milestone 3 - Sourcing and Structural Signal Agents

Purpose:

- Convert document events into the six AAE structural signals.

Deliverables:

- `engine_core/aae_sourcing_agent.py`
- `engine_core/aae_structural_signal_agent.py`
- Six-signal vector.
- Structural conviction score.
- Evidence-linked justifications.

Done criteria:

- A company can receive a versioned structural signal state.
- High-conviction alerts fire only when evidence-backed thresholds are met.

## Milestone 4 - Macro and Risk Agents

Purpose:

- Add sector/macro context and thesis-break monitoring.

Deliverables:

- `engine_core/aae_macro_agent.py`
- `engine_core/aae_execution_monitoring_agent.py`
- Sector macro scoring.
- Risk dashboard state.
- Thesis-at-risk alerts.

Done criteria:

- Macro and risk outputs are stored separately from PRDE financial scores.
- Risk alerts cite source data or source events.

## Milestone 5 - Orchestrator and Re-Rating Candidate Profile

Purpose:

- Combine financial, structural, macro, risk, valuation, and MRI timing overlays into one investable research object.

Deliverables:

- `engine_core/aae_orchestrator.py`
- Re-rating Candidate Profile schema.
- Re-rating probability score.
- Thesis JSON with versioning.
- Score history.

Done criteria:

- Every ranked candidate can be traced to feature snapshot, structural evidence, macro/risk state, and scoring version.

## Milestone 6 - Analyst Console

Purpose:

- Make AAE usable by human analysts.

Deliverables:

- Candidate dashboard.
- Company page.
- Event view.
- Structural signal timeline.
- Financial fingerprint charts.
- Risk dashboard.
- Analyst accept/reject/modify workflow.

Done criteria:

- Analysts can review, modify, and audit machine-generated theses.
- Analyst feedback is stored with user, timestamp, and justification.

## Milestone 7 - Learning and Calibration

Purpose:

- Improve thresholds and weights using labeled historical re-rating cases.

Deliverables:

- Historical case library.
- Backtest framework for score changes.
- Analyst feedback export.
- Threshold calibration reports.

Done criteria:

- Historical wins and misses are reviewable.
- Score changes can be compared against later re-rating outcomes.

## Immediate Next Step

Complete Milestone 0 using the existing PRDE TODO:

```bash
mkdir -p data
cp docs/prde_financials_template.csv data/prde_financials_seed.csv
python scripts/import_prde_financials.py data/prde_financials_seed.csv --dry-run
python scripts/import_prde_financials.py data/prde_financials_seed.csv
python scripts/verify_prde_import.py --min-companies 10 --min-years 5
python engine_core/prde_feature_engine.py --limit 20 --dry-run
python engine_core/prde_feature_engine.py --limit 20
```

After that, implement Milestone 1 before introducing document RAG or event agents.

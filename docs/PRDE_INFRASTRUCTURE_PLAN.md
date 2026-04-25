# PRDE Infrastructure Plan

## Product

PRDE - PE Re-Rating Discovery Engine

## Purpose

This document maps the PRDE PRD onto the existing MRI platform and identifies what can be reused, what must be added, and the smallest practical implementation path.

PRDE should be treated as a new fundamentals intelligence layer inside the existing MRI monolith, not as a separate system. MRI already owns market data, trend/regime scoring, portfolio/watchlist context, email delivery, admin visibility, and scheduled pipeline execution. PRDE adds financial statement ingestion, fundamental feature engineering, LLM-assisted analyst scoring, and investor reports.

## Existing Infrastructure We Can Reuse

### 1. Application Architecture

Reuse the current FastAPI monolith, React/Vite frontend, and Railway deployment.

Current MRI already runs as a single service with API routes, engine modules, scheduled scripts, and shared database access. PRDE should follow that pattern:

- New engine modules under `engine_core/`
- New API router under `api/`
- New schema bootstrap additions in `api/schema.py`
- New scheduled script under `scripts/`
- Optional admin UI additions in `frontend/`

No microservice split is required for the MVP.

### 2. Database

Reuse Neon PostgreSQL.

MRI already stores:

- `daily_prices`
- `stock_scores`
- `market_regime`
- `client_watchlist`
- `client_external_holdings`
- `email_log`
- `system_audit_logs`
- `swing_trades`

PRDE can join against existing price, trend, and regime data rather than recreate price infrastructure.

Existing useful joins:

- PRDE company symbol -> `daily_prices.symbol`
- PRDE timing filter -> latest `stock_scores.total_score`
- PRDE market protection -> latest `market_regime`
- PRDE user relevance -> `client_watchlist` and `client_external_holdings`

### 3. Scheduler and Pipeline

Reuse the existing daily pipeline pattern in `run_daily_pipeline.sh`.

PRDE does not need to run daily at first. A separate 3-day scheduled job can be added later, but the implementation can begin as a manually runnable script:

```bash
python scripts/run_prde_pipeline.py
```

Once stable, it can be added as:

- A GitHub Actions cron every 3 days, or
- A Railway scheduled job, or
- A guarded step in the existing pipeline that only runs when due.

### 4. Email Delivery

Reuse `engine_core/email_service.py` and AWS SES.

MRI already supports:

- Signal emails
- STEE alerts
- Password reset emails
- Portfolio review emails
- Generic alert emails
- `email_log`

PRDE needs only a new email builder and sender, for example:

- `build_prde_report_email_html(...)`
- `send_prde_report_emails(...)`

### 5. Audit and Monitoring

Reuse `system_audit_logs` and `scripts/pipeline_health_monitor.py` patterns.

PRDE should log:

- Data ingestion status
- Number of companies scanned
- Number of agent runs
- LLM failures or skipped companies
- Final candidate count
- Email delivery status

This is important because PRDE has more moving parts than MRI scoring. Silent failure prevention should be designed in from day one.

### 6. Admin Dashboard

Reuse the current Admin Dashboard model.

Initial admin visibility can be minimal:

- Latest PRDE run status
- Top candidates
- Company report lookup
- Failed/skipped companies
- Agent confidence warnings

This can be added after the backend pipeline is working.

### 7. Existing Intelligence Layer

MRI already has a trend/regime layer. PRDE should not duplicate this.

PRDE should use MRI as an entry-timing and risk overlay:

- Fundamental PRDE score says: "Is this company likely to re-rate?"
- MRI trend score says: "Is the market currently recognizing it?"
- Market regime says: "Is the environment favorable?"
- STEE can later help with tactical entry timing.

This creates a clean separation:

- PRDE = transformation discovery
- MRI = trend and regime validation
- STEE = swing execution timing

## What We Need To Add

### 1. Financial Data Source

This is the biggest missing dependency.

MRI currently has price data, not 5-10 years of financial statements. PRDE requires:

- Revenue
- EBITDA
- PAT
- ROCE
- Capex
- Employee cost
- Total assets
- Segment data
- PE
- EV/EBITDA
- PB
- Debt/equity
- Sector and industry medians

Data source options:

- Manual CSV import for MVP
- Screener-style exported financials for Indian equities
- Paid API later
- US fundamentals API later for secondary market support

Recommendation: start with manual CSV import for 50-100 Indian companies. This avoids spending time on brittle scraping before the scoring framework is validated.

### 2. PRDE Schema

The PRD schema is directionally right, but should be adapted to MRI conventions:

- Use `BIGSERIAL` or UUID where appropriate.
- Use `TIMESTAMPTZ`, not plain `TIMESTAMP`.
- Add uniqueness constraints to avoid duplicate annual rows.
- Keep agent outputs versioned by `run_id`.
- Store feature snapshots so reports are reproducible.
- Avoid naming a table `triggers` because it can be confusing beside database triggers.

Recommended MVP tables:

```sql
prde_companies
prde_financials_annual
prde_ratios_annual
prde_feature_snapshots
prde_agent_scores
prde_final_scores
prde_report_events
prde_jobs
```

Key design choice: every final score should be traceable to the exact feature JSON and agent outputs used to produce it.

### 3. Feature Engineering Engine

Add:

```text
engine_core/prde_feature_engine.py
```

Responsibilities:

- Load annual financials and ratios
- Compute revenue CAGR
- Compute EBITDA CAGR
- Compute PAT CAGR
- Compute EBITDA/PAT growth versus revenue growth
- Compute margin trends
- Compute ROCE trend
- Compute asset turnover trend
- Compute capex intensity
- Compute debt risk features
- Produce structured JSON per company

This should be deterministic Python, not LLM-driven.

### 4. Agent Runner

Add:

```text
engine_core/prde_agent_runner.py
```

Responsibilities:

- Accept structured feature JSON
- Run the 11 agent prompts
- Validate every response against a strict JSON schema
- Store score, confidence, reasoning, flags, and model metadata
- Retry safely on malformed outputs
- Continue scanning other companies if one company fails

Important: agents should not fetch data themselves in MVP. They should analyze only the feature JSON generated by the pipeline.

### 5. Scoring Engine

Add:

```text
engine_core/prde_scoring_engine.py
```

Responsibilities:

- Apply the weighted scoring formula
- Include risk as a penalty or inverse score
- Classify companies:
  - Strong Candidate
  - Emerging Candidate
  - Watchlist
  - Avoid
- Join with MRI trend/regime data for optional timing overlay

Suggested MVP score formula:

```text
base_score =
  operating_leverage * 0.20
  + revenue_growth * 0.15
  + margin_expansion * 0.15
  + roce * 0.15
  + tam_expansion * 0.10
  + industry_tailwind * 0.10
  + predictability * 0.10
  + valuation_gap * 0.05

final_score = base_score - risk_penalty
```

### 6. Report Generator

Add:

```text
engine_core/prde_report_generator.py
```

Report output should be JSON first, HTML second.

JSON report shape:

```json
{
  "summary": "...",
  "key_drivers": [],
  "triggers": [],
  "risks": [],
  "valuation_gap": "...",
  "mri_timing_overlay": "...",
  "final_verdict": "..."
}
```

The API and email layer can render this JSON into human-readable output.

### 7. API Routes

Add:

```text
api/prde.py
```

MVP endpoints:

- `GET /api/prde/candidates`
- `GET /api/prde/companies/{symbol}`
- `POST /api/prde/scan`
- `GET /api/admin/prde/jobs`
- `GET /api/admin/prde/failures`

Admin-only endpoints should be protected with the existing admin auth dependency.

### 8. Frontend Screens

Add only after backend is proven.

Suggested first screens:

- PRDE Candidates table
- Company report detail
- Admin run status

Avoid charts for MVP because the PRD explicitly asks for actionable reports with no manual interpretation.

### 9. LLM Provider Configuration

The current project does not appear to have a dedicated LLM client abstraction.

Add:

```text
engine_core/llm_client.py
```

Required env vars:

```text
OPENAI_API_KEY
PRDE_LLM_MODEL
PRDE_LLM_MAX_CONCURRENCY
PRDE_LLM_TIMEOUT_SECONDS
PRDE_LLM_DAILY_BUDGET
```

The pipeline should fail closed if `OPENAI_API_KEY` is absent and PRDE agent scoring is requested.

### 10. Cost and Rate Controls

PRDE can become expensive because it runs many agents per company.

Example:

```text
100 companies * 11 agents = 1,100 LLM calls per scan
```

MVP controls needed:

- Limit max companies per run
- Cache agent outputs per `feature_snapshot_hash`
- Skip re-analysis when financial data has not changed
- Run master agent only after deterministic weighted score is computed
- Store raw structured output for auditability

## Recommended MVP Scope

The first PRDE milestone should not scan the full market.

Recommended MVP:

- India only
- 50-100 companies
- Annual data only
- Manual CSV ingestion
- No segment-level parsing initially
- 8 scoring agents plus master decision
- Email disabled by default until reports are reviewed
- Admin-triggered run before scheduler automation

Agents to include in MVP:

- Operating Leverage
- Revenue Acceleration
- Margin Expansion
- ROCE
- Predictability
- Valuation Gap
- Risk
- Master Decision

Agents to defer:

- TAM & Expansion
- Industry Tailwind
- Integration

Reason: the deferred agents require external narrative/sector data that is harder to source reliably. The core rerating signal can be tested first using financial statements and ratios.

## Implementation Phases

### Phase 1 - Data Foundation

Deliverables:

- PRDE schema bootstrap
- CSV import script
- Company mapping to MRI symbols
- Annual financial and ratio storage
- Basic data quality report

Done criteria:

- 50+ companies loaded
- No duplicate company/year rows
- Missing required fields reported clearly
- Data import is repeatable

### Phase 2 - Deterministic Feature Engine

Deliverables:

- `prde_feature_engine.py`
- Feature JSON per company
- Feature snapshot table
- Unit or script-level validation on sample companies

Done criteria:

- Revenue, EBITDA, PAT, margin, ROCE, capex, and debt features computed
- Feature snapshots are persisted
- Same input data produces same feature hash

### Phase 3 - Agent and Scoring MVP

Deliverables:

- LLM client
- Agent prompt registry
- JSON schema validation
- Agent score persistence
- Weighted final score

Done criteria:

- A run can score 10 companies end to end
- Bad LLM output is retried or marked failed
- Failed companies do not kill the full job
- Final scores are reproducible from stored feature snapshots and agent outputs

### Phase 4 - Reports

Deliverables:

- JSON report generator
- HTML/email renderer
- Candidate ranking endpoint
- Company report endpoint

Done criteria:

- Each candidate has summary, drivers, triggers, risks, and verdict
- Reports include "not financial advice" language
- Reports can be reviewed in admin before email delivery

### Phase 5 - Scheduler and Delivery

Deliverables:

- `scripts/run_prde_pipeline.py`
- 3-day scheduler
- Email delivery
- Audit log integration
- Health monitor checks

Done criteria:

- Job runs incrementally
- Unchanged companies are skipped
- Candidate emails are sent only after successful score/report generation
- Admin can see run status and failures

## How PRDE Should Use MRI Signals

PRDE should not replace MRI scores. It should enrich them.

Suggested combined interpretation:

| PRDE | MRI Trend | Market Regime | Meaning |
| --- | --- | --- | --- |
| High | High | Bullish | Strong rerating candidate with timing support |
| High | Low | Bullish/Sideways | Fundamental watchlist; market has not confirmed |
| High | High | Bearish | Candidate exists, but defer exposure |
| Low | High | Bullish | Momentum without rerating thesis |
| Low | Low | Any | Avoid |

This lets the system preserve the existing compliance posture: it provides structured analytics and risk context rather than direct buy/sell recommendations.

## Risks

### Data Quality Risk

Financial statement data is harder than price data. Incorrect annual data will produce polished but wrong reports.

Mitigation:

- Start with manual CSV
- Add source and import timestamp
- Store feature snapshots
- Flag missing or suspicious fields

### LLM Hallucination Risk

Agents may invent explanations if asked to reason beyond the input data.

Mitigation:

- Agents receive only structured JSON
- Prompt says not to infer absent data
- Output must include confidence
- Report generator must cite computed features

### Cost Risk

Full market scans with 11 agents can become expensive.

Mitigation:

- Cache by feature hash
- Cap companies per run
- Add budget env vars
- Use deterministic pre-filter before LLM calls

### Compliance Risk

The output can look like investment advice.

Mitigation:

- Use "candidate", "watchlist", and "risk" language
- Avoid imperative buy/sell wording
- Include disclaimers
- Keep MRI/PRDE as decision-support analytics

## Next Smallest Logical Step

Create the PRDE data foundation first.

The smallest useful implementation step is:

1. Add PRDE tables to `api/schema.py`.
2. Create a CSV format contract for annual financials and ratios.
3. Create `scripts/import_prde_financials.py`.
4. Load a small test universe of 10-20 companies.
5. Generate a data quality report before any LLM agents are added.

Reasoning:

The PRD depends on financial data. Without trusted financials, the agents and reports will only make incorrect analysis sound convincing. A small, repeatable data import gives the rest of the system a stable foundation and follows the existing MRI pattern of fixing data correctness before UI or automation.

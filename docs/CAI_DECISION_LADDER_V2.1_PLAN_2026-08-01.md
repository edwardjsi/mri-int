# CAI Decision Ladder V2.1 — Final Ship-Ready Engineering Spec

This is the normalized, implementation-ready version of the execution plan. It removes the last ambiguity by making **ALERT** a canonical ladder state, not an orthogonal flag, and defines the hierarchy, contracts, persistence, notifications, and test strategy in ship-ready form.

## 1. Objective

Implement CAI Decision Ladder V2.1 as a deterministic portfolio decision system that assigns every holding exactly one canonical state, in strict priority order, with explainability, thresholds, triggers, expiry, stability, and a persistent decision ledger.

### Canonical states
- ADD.
- HOLD.
- ALERT.
- STRUCTURE.
- QUIT.

### Decision order
The engine must evaluate states in this exact precedence:
1. QUIT.
2. STRUCTURE.
3. ALERT.
4. ADD.
5. HOLD.

If multiple states are valid, the highest-priority state wins. This makes resolution deterministic and auditable.

## 2. Canonical contract

### DecisionEvaluation
The API must return a strictly typed `DecisionEvaluation` object for every evaluation.

Required fields:
- `position_id`.
- `symbol`.
- `decision_state`.
- `decision_confidence`.
- `decision_stability`.
- `decision_expiry`.
- `rule_satisfaction_score`.
- `why`.
- `why_not_add`.
- `thresholds`.
- `triggered_rules`.
- `rule_categories`.
- `portfolio_context`.
- `last_updated`.
- `history`.
- `engine_version`.
- `rule_set_version`.
- `schema_version`.

### Field semantics
- `decision_state`: one of `ADD`, `HOLD`, `ALERT`, `STRUCTURE`, `QUIT`.
- `decision_confidence`: float from 0.0 to 1.0.
- `decision_stability`: float from 0.0 to 1.0.
- `decision_expiry`: ISO-8601 timestamp after which a fresh evaluation is required.
- `rule_satisfaction_score`: float from 0.0 to 1.0. Formula: `(Sum of weights for all passed rules) / (Total weight of all globally applicable rules across all categories)`.
- `why_not_add`: mandatory whenever state is not `ADD`.
- `triggered_rules`: list of rule IDs that fired.
- `thresholds`: computed threshold objects, not states.
- `history`: prior transitions and ledger references.
- `engine_version`, `rule_set_version`, `schema_version`: semantic versions (e.g. `2.1.0`) ensuring deterministic backtesting and auditability.

## 3. Decision model

### 3.1 States
| State | Meaning | Action |
|---|---|---|
| ADD | Position deserves new capital | Add next tranche |
| HOLD | Trend is healthy | Do nothing |
| ALERT | Early warning | Watch closely |
| STRUCTURE | Trend quality broken | Stop adding, tighten risk |
| QUIT | Thesis invalidated | Exit after confirmation |

### 3.2 Ladder behavior
- A position always has exactly one state.
- States can move up or down as evidence changes.
- Recovery is allowed.
- State snapshots are derived, not manually stored as the source of truth.

### 3.3 Transition validation
The engine enforces explicit transition validation rules to prevent illegal state jumps without required evidence.
- A position cannot jump from `QUIT` directly to `ADD` without passing through a confirmation state (e.g., `HOLD` or `STRUCTURE` first).
- Any illegal transition must fail closed: the engine will reject the state change, return the previous state as the active state, and log an explicit transition violation error for auditing.

## 4. Thresholds and triggers

### 4.1 Threshold model
Thresholds are computed facts, not states.

Examples:
- Breakout threshold.
- Alert threshold.
- Structure threshold.
- Quit threshold.

Each threshold must have:
- threshold type.
- threshold value.
- confidence.
- reason.
- triggered rules.
- valid from.
- valid until.

### 4.2 Trigger types
The engine must support both:
- **Price triggers**: resistance, support, EMA violations, breakout confirmation.
- **Event triggers**: institutional selling, weak sales growth, RS deterioration, market regime weakness.

## 5. Explainability

Every evaluation must include:

- A plain-language reason.
- A `why_not_add` explanation when the state is not ADD.
- Rule satisfaction score.
- Confidence score.
- Stability score.
- Triggered rules.
- Rule categories.
- Threshold rationale.

### Rule categories
- Technical.
- Fundamental.
- Capital Allocation.
- Risk.
- Portfolio.
- Market.

### Why Not Add?
This is mandatory for all non-ADD states.

Examples:
- Breakout not confirmed.
- Volume weak.
- Better candidate exists.
- Portfolio weight already full.
- Market regime not supportive.

## 6. Stability and expiry

### 6.1 Stability
Stability measures the likelihood that the current state will remain unchanged over the next evaluation window.

Computation formula:
- `flip_count`: Number of state transitions in the trailing 30-day window.
- `recency_penalty`: `1.0 / (days_since_last_flip + 1)`.
- `decision_stability = max(0.0, 1.0 - (flip_count * 0.1) - (recency_penalty * 0.5))`.
- Higher flip frequency or extremely recent flips linearly degrade the stability score toward `0.0`.

### 6.2 Expiry
Every decision must expire.

Behavior (Stale-Response Contract):
- If `decision_expiry` has passed, the backend must synchronously force a fresh engine evaluation before returning a response.
- If fresh evaluation fails (e.g., market data unavailable), the API must return the last known state with a strict marker: `{"is_stale": true, "stale_reason": "evaluation_failed"}` instead of returning a generic error.
- Clients must surface `is_stale` visually to warn the user.

## 7. Ledger

### 7.1 Decision ledger
The decision ledger is append-only and stores every state transition and evaluation snapshot.

Required fields:
- from_state.
- to_state.
- reasoning_snapshot.
- confidence.
- stability.
- rule_satisfaction_score.
- timestamp.
- expiry.
- triggered_rules.
- threshold references.

### 7.2 Purpose
- Audit trail.
- Backtesting.
- Learning loop.
- Debugging rule behavior.
- Historical state reconstruction.

## 8. Idempotent notifications

### 8.1 Notification rule
Notifications fire only when the state changes.

### 8.2 Dedupe rule
Store an idempotency key such as:
- `(symbol, to_state, date)` for daily batching, or
- `(position_id, transition_id)` for stricter uniqueness.

### 8.3 Suppression behavior
Same-day re-evaluations that return the same state must be suppressed.

## 9. API requirements

### Evaluate position
`POST /api/v2/positions/{positionId}/evaluate`

Returns `DecisionEvaluation`.

### Get decisions
`GET /api/v2/positions/{positionId}/decisions`

Returns evaluation snapshots and transition history.

### Get ledger
`GET /api/v2/positions/{positionId}/ledger`

Returns append-only ledger records.

### Portfolio health
`GET /api/v2/portfolios/{portfolioId}/health`

Returns counts by state and health metrics.

### Decision distribution
`GET /api/v2/portfolios/{portfolioId}/decision-distribution`

Returns portfolio-wide state counts.

### Notification subscriptions
`POST /api/v2/notifications/subscriptions`

Registers notification targets.

## 10. Persistence model

### Tables
- `decision_snapshots`
- `threshold_definitions`
- `state_transitions`
- `decision_ledger`
- `portfolio_health_snapshots`
- `notification_locks`

### Storage rules
- Snapshots store current evaluation output.
- Thresholds store computed threshold artifacts.
- Transitions store state changes.
- Ledger stores every evaluation history row.
- Notification locks prevent duplicates.

## 11. Engine behavior

### Evaluation pipeline
1. Collect market, price, and portfolio inputs.
2. Compute thresholds.
3. Evaluate QUIT conditions.
4. Evaluate STRUCTURE conditions.
5. Evaluate ALERT conditions.
6. Evaluate ADD conditions.
7. Default to HOLD.
8. Compute confidence, stability, and expiry.
9. Generate explanation fields.
10. Persist snapshot and ledger entry.
11. Emit transition notification if state changed.

### Determinism requirement
The same input snapshot must always produce the same output.

## 12. Test strategy

### Golden scenarios
The test suite must include the following:
- ADD vs STRUCTURE → STRUCTURE wins.
- ADD vs QUIT → QUIT wins.
- HOLD vs ALERT → ALERT wins.
- ALERT vs STRUCTURE → STRUCTURE wins.
- Recovery from QUIT → possible if evidence improves.
- Expired snapshot → fresh evaluation forced.
- Same-day repeated evaluation → notification suppressed.

### Test types
- Unit tests for rule evaluation.
- Contract tests for `DecisionEvaluation`.
- Transition tests for ladder movement.
- Idempotency tests for notifications.
- Snapshot persistence tests.
- Determinism tests for conflicting signals.

## 13. UI requirements

### Holdings table
Show:
- Decision.
- Confidence.
- Stability.
- Next tranche.
- Why.
- Why Not Add?
- Expiry.
- Portfolio %
- Sector %

### Widgets
- Portfolio Health Score.
- Decision Distribution.
- Ledger Timeline.
- Audit Trail.

### Visual semantics
- ADD = green.
- HOLD = neutral.
- ALERT = yellow.
- STRUCTURE = orange.
- QUIT = red.

## 14. Implementation phases

### Phase 1: Core schema
- Pydantic domain models.
- Database migrations.
- Repository layer.

### Phase 2: Engine
- Rule hierarchy.
- Threshold computation.
- Explainability.
- Stability and expiry.

### Phase 3: API
- Position evaluation endpoint.
- Decision and ledger endpoints.
- Portfolio endpoints.

### Phase 4: Ledger and notifications
- Append-only ledger writes.
- Transition tracking.
- Idempotent notifications.

### Phase 5: UI
- Table columns.
- Widgets.
- Ledger panel.

## 15. Acceptance criteria

The feature is complete when:
1. Every holding resolves to one canonical state.
2. Hierarchy is deterministic.
3. Thresholds are separate from states.
4. Every threshold has confidence and reason.
5. Every non-ADD output has `why_not_add`.
6. Stability and expiry are computed and stored.
7. Ledger is append-only and queryable.
8. Notifications are idempotent.
9. Golden scenarios pass.
10. UI surfaces decision, confidence, and history clearly.

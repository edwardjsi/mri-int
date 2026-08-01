# CAI Decision Ladder V2.1 — Full Implementation Pack

CAI Decision Ladder V2.1 is a portfolio operating system that assigns every holding exactly one canonical decision state, explains why that decision was made, tracks how stable it is, and records every change in a first-class decision ledger. The design separates **decision states**, **thresholds**, **triggers**, and **history** so the AI team can implement it deterministically and auditably.

***

## 1. Product summary

CAI Decision Ladder V2.1 replaces binary stock recommendations with a layered decision system that answers the full lifecycle of a position.

Every holding must always resolve to exactly one of these states:

- ADD
- HOLD
- ALERT
- STRUCTURE
- QUIT

The system must evaluate positions in a strict hierarchy:

1. Can I QUIT?
2. Can I PROTECT?  
3. Can I ADD?
4. Otherwise HOLD.

This makes the engine deterministic when multiple conditions are true at once.

***

## 2. Product goals

### Primary goals
- Replace Buy/Hold/Sell thinking with a portfolio decision ladder.
- Separate decision states from price thresholds.
- Make every decision explainable.
- Generate notifications only on meaningful state transitions.
- Maintain a persistent decision ledger for learning and backtesting.

### Secondary goals
- Improve investor discipline.
- Reduce alert noise.
- Support portfolio-wide health monitoring.
- Provide an audit trail for all decisions and threshold changes.

***

## 3. Core design principles

1. One stock, one active state.
2. State must be derived from objective rules.
3. States, thresholds, and triggers are distinct entities.
4. The decision hierarchy must resolve conflicts deterministically.
5. Every threshold must have confidence, reason, and supporting evidence.
6. Every decision must expire.
7. Every decision change must be stored in the decision ledger.
8. Explanations must be human-readable and machine-readable.

***

## 4. Decision ladder

### 4.1 States
| State | Meaning | Investor action |
|---|---|---|
| ADD | Position deserves more capital | Add next tranche |
| HOLD | Trend remains healthy | Do nothing |
| ALERT | Early warning | Watch closely |
| STRUCTURE | Trend quality broken | Stop adding, tighten risk |
| QUIT | Thesis invalidated | Exit after confirmation |

### 4.2 State order
**ADD → HOLD → ALERT → STRUCTURE → QUIT**

### 4.3 Recovery path
**QUIT → STRUCTURE → ALERT → HOLD → ADD**

A position may move in either direction as evidence changes.

***

## 5. Decision hierarchy

The engine must evaluate in this order:

1. **QUIT**
2. **STRUCTURE / PROTECT**
3. **ADD**
4. **HOLD**

### 5.1 Conflict resolution
If a stock satisfies multiple candidate states, the highest-priority state wins.

Examples:
- If a stock qualifies for both ADD and ALERT, the engine must check whether QUIT or STRUCTURE rules apply first. If not, ADD can win.
- If structural failure is present, ADD must never override STRUCTURE or QUIT.
- If the position is healthy but not strong enough for ADD, HOLD wins unless ALERT conditions are clearly stronger.

### 5.2 Deterministic rule
The engine must never return two active states for one holding.

***

## 6. State definitions

### 6.1 ADD
The stock has earned additional capital.

**Investor action:** Add next tranche.

**Typical evidence:**
- Fresh breakout.
- Healthy pullback confirmed.
- New weekly higher high.
- Relative strength improving.
- Volume expansion.
- MRI score remains high.
- Portfolio allocation allows adding.
- No superior MRI candidate exists.
- Market regime supports deployment.

**Output requirements:**
- Decision state = `ADD`
- Confidence score
- Rule satisfaction score
- Triggered rules
- Why not add? explanation for non-ADD states
- Thresholds and expiry
- Stability score

***

### 6.2 HOLD
The trend remains healthy and no action is required.

**Investor action:** Do nothing.

**Typical evidence:**
- Higher highs.
- Higher lows.
- Trend intact.
- Healthy consolidation.
- Position already fully allocated.

**Output requirements:**
- Decision state = `HOLD`
- Confidence score
- Why not add?
- Stability score
- Expiry window

***

### 6.3 ALERT
Early warning; not enough to reduce yet.

**Investor action:** Watch closely, no trade.

**Typical evidence:**
- Momentum slowing.
- Relative strength weakening.
- Volume drying up.
- Repeated failed breakout attempts.
- Trend flattening.
- Extended sideways movement.
- Late-stage trend.

**Output requirements:**
- Decision state = `ALERT`
- Confidence score
- Triggered rules
- Reason text
- Stability score
- Expiry window

***

### 6.4 STRUCTURE
Trend quality is deteriorating and capital protection begins.

**Investor action:** Stop adding, raise stop, prepare exit plan.

**Typical evidence:**
- Weekly higher-low broken.
- EMA alignment deteriorating.
- Relative strength collapsing.
- Failed breakout.
- Distribution.
- Heavy institutional selling.

**Output requirements:**
- Decision state = `STRUCTURE`
- Confidence score
- Triggered rules
- Reason text
- Thresholds
- Stability score
- Expiry window

***

### 6.5 QUIT
Objective trend failure; original thesis no longer valid.

**Investor action:** Exit after confirmation.

**Typical evidence:**
- Weekly close below structural support.
- Second weekly confirmation.
- Multiple lower highs.
- Multiple lower lows.
- Relative strength deterioration.
- Major distribution.

**Output requirements:**
- Decision state = `QUIT`
- Confidence score
- Triggered rules
- Reason text
- Thresholds
- Stability score
- Expiry window

***

## 7. Decision entities

The system must model the following as separate entities.

### 7.1 DecisionState
The final state assigned to the position.

Values:
- ADD
- HOLD
- ALERT
- STRUCTURE
- QUIT

### 7.2 Threshold
A measurable level or condition used to support a decision.

Thresholds are not the same as states.

Examples:
- Breakout price = ₹7,250
- Alert price = ₹6,900
- Structure price = ₹6,500
- Quit price = ₹6,250

### 7.3 Trigger
A rule or condition that caused the decision.

Triggers can be:
- Price triggers.
- Event triggers.

### 7.4 DecisionLedgerEntry
Historical record of a decision at a point in time.

### 7.5 RuleCategory
Grouping for explainability:
- Technical
- Fundamental
- Capital Allocation
- Risk
- Portfolio
- Market

***

## 8. Rule hierarchy and scoring

### 8.1 Evaluation order
1. QUIT rules
2. STRUCTURE / PROTECT rules
3. ADD rules
4. HOLD fallback

### 8.2 Rule satisfaction score
Each decision should produce a score such as `8 / 10`.

The score should show:
- Passed rules.
- Failed rules.
- Total applicable rules.

### 8.3 Confidence score
Each decision and each threshold must have a confidence score from 0–100.

Confidence should reflect:
- Strength of evidence.
- Agreement across rule categories.
- Distance from invalidation.
- Stability of trend.
- Portfolio context.

### 8.4 Decision stability
A separate score from 0–100 showing how likely the decision is to change soon.

Examples:
- 92% = robust decision.
- 54% = borderline decision.

### 8.5 Decision expiry
Every decision must have a validity period.

Examples:
- Valid until Friday close.
- Expires after 5 trading days.

***

## 9. Explainability requirements

Every decision must include:

- Decision state.
- Confidence.
- Rule satisfaction.
- Stability.
- Expiry.
- Triggered rules.
- Why this decision.
- Why not the next stronger decision.
- Threshold rationale.

### 9.1 Why Not Add?
If the final state is not ADD, the system must provide a `Why Not Add?` explanation.

Examples:
- Breakout not confirmed.
- Volume weak.
- Better MRI candidate exists.
- Already 10% portfolio weight.

### 9.2 Threshold reasons
Every threshold must carry a reason.

Example:
- Alert threshold: ₹6,900.
- Reason: Loss of momentum and RS deterioration.
- Confidence: 87%.

***

## 10. Price triggers and event triggers

The system must distinguish between two trigger classes.

### 10.1 Price triggers
Price-based conditions.

Examples:
- Breakout above resistance.
- Weekly close below support.
- Higher-low violation.

### 10.2 Event triggers
Non-price conditions that still affect the decision.

Examples:
- Institutional selling.
- Quarterly sales growth < 15%.
- RS deterioration.
- Market regime deterioration.
- Weak volume expansion.

Event triggers may move a stock into ALERT or STRUCTURE even without an exact price breach.

***

## 11. Inputs

The engine should consume:

- MRI Score
- Weekly Trend Score
- Relative Strength Score
- Breakout Quality
- Volume Score
- Market Regime
- Capital Allocation Rules
- Position Size
- Sector Exposure
- Portfolio Risk
- Current Price
- Days Since Entry
- Current Gain
- Maximum Gain
- Fundamental event inputs
- Market event inputs

***

## 12. Output contract

Each evaluation should return a canonical object.

### DecisionEvaluation schema
```json
{
  "symbol": "DIVISLABS",
  "currentPrice": 7210,
  "decisionState": "ADD",
  "decisionConfidence": 96,
  "decisionStability": 92,
  "decisionExpiry": "2026-08-08T15:30:00+05:30",
  "ruleSatisfaction": {
    "score": "8/10",
    "passed": [
      "weekly_breakout_confirmed",
      "volume_expansion",
      "rs_improving",
      "mri_high",
      "market_healthy"
    ],
    "failed": [
      "better_candidate_absent",
      "capital_constraint_clear"
    ]
  },
  "why": "Fresh breakout above weekly resistance with strong MRI and improving relative strength.",
  "whyNotAdd": null,
  "thresholds": {
    "breakout": {
      "price": 7250,
      "confidence": 94,
      "reason": "Weekly resistance cleared on strong volume.",
      "triggeredRules": [
        "weekly_breakout_confirmed",
        "volume_expansion"
      ]
    },
    "alert": {
      "price": 6900,
      "confidence": 88,
      "reason": "Momentum would weaken below this level.",
      "triggeredRules": [
        "momentum_slowing",
        "rs_deterioration"
      ]
    },
    "structure": {
      "price": 6500,
      "confidence": 90,
      "reason": "Higher-low violation would indicate structural damage.",
      "triggeredRules": [
        "weekly_higher_low_broken"
      ]
    },
    "quit": {
      "price": 6250,
      "confidence": 92,
      "reason": "Weekly trend failure and thesis invalidation.",
      "triggeredRules": [
        "weekly_close_below_support",
        "second_weekly_confirmation"
      ]
    }
  },
  "triggeredRules": [
    {
      "rule": "weekly_breakout_confirmed",
      "category": "Technical",
      "type": "price"
    },
    {
      "rule": "volume_expansion",
      "category": "Technical",
      "type": "event"
    },
    {
      "rule": "rs_improving",
      "category": "Technical",
      "type": "event"
    },
    {
      "rule": "mri_high",
      "category": "Fundamental",
      "type": "event"
    }
  ],
  "portfolioContext": {
    "portfolioPct": 6.2,
    "sectorPct": 14.1,
    "cashAvailable": true,
    "betterCandidateExists": false
  },
  "nextTrancheAmount": 50000,
  "lastUpdated": "2026-08-01",
  "history": [
    {
      "from": "HOLD",
      "to": "ADD",
      "date": "2026-08-01",
      "reason": "Breakout confirmed"
    }
  ]
}
```

***

## 13. Data model

### 13.1 Position
Represents one holding.

Fields:
- positionId
- portfolioId
- symbol
- exchange
- quantity
- entryPrice
- currentPrice
- costBasis
- daysSinceEntry
- currentGainPct
- maxGainPct
- portfolioPct
- sectorPct
- createdAt
- updatedAt

### 13.2 DecisionSnapshot
Represents one evaluation result.

Fields:
- snapshotId
- positionId
- decisionState
- decisionConfidence
- decisionStability
- decisionExpiry
- ruleSatisfactionScore
- reason
- whyNotAdd
- thresholdsJson
- triggeredRulesJson
- mriScore
- caiScore
- trendScore
- rsScore
- volumeScore
- regimeScore
- evaluatedAt

### 13.3 ThresholdDefinition
Represents a threshold associated with a decision.

Fields:
- thresholdId
- positionId
- thresholdType
- thresholdValue
- confidence
- reason
- triggeredRulesJson
- validFrom
- validUntil

### 13.4 StateTransition
Represents movement from one state to another.

Fields:
- transitionId
- positionId
- fromState
- toState
- reason
- triggeredRulesJson
- confidence
- evaluatedAt
- notifiedAt

### 13.5 DecisionLedgerEntry
Represents the full historical decision record.

Fields:
- ledgerEntryId
- positionId
- decisionDate
- decisionState
- decisionPrice
- ruleScore
- confidence
- stability
- result
- followUpReturnPct
- notes
- createdAt

### 13.6 PortfolioHealthSnapshot
Represents portfolio-wide decision distribution.

Fields:
- snapshotId
- portfolioId
- addCount
- holdCount
- alertCount
- structureCount
- quitCount
- totalPositions
- healthScore
- evaluatedAt

***

## 14. Database schema

### positions
- id
- portfolio_id
- symbol
- exchange
- quantity
- entry_price
- current_price
- cost_basis
- days_since_entry
- current_gain_pct
- max_gain_pct
- portfolio_pct
- sector_pct
- created_at
- updated_at

### decision_snapshots
- id
- position_id
- decision_state
- decision_confidence
- decision_stability
- decision_expiry
- rule_satisfaction_score
- reason
- why_not_add
- thresholds_json
- triggered_rules_json
- mri_score
- cai_score
- trend_score
- rs_score
- volume_score
- regime_score
- evaluated_at

### threshold_definitions
- id
- position_id
- threshold_type
- threshold_value
- confidence
- reason
- triggered_rules_json
- valid_from
- valid_until

### state_transitions
- id
- position_id
- from_state
- to_state
- reason
- triggered_rules_json
- confidence
- evaluated_at
- notified_at

### decision_ledger
- id
- position_id
- decision_date
- decision_state
- decision_price
- rule_score
- confidence
- stability
- result
- follow_up_return_pct
- notes
- created_at

### portfolio_health_snapshots
- id
- portfolio_id
- add_count
- hold_count
- alert_count
- structure_count
- quit_count
- total_positions
- health_score
- evaluated_at

***

## 15. API specification

### 15.1 Evaluate position
**POST** `/api/v2/positions/{positionId}/evaluate`

Returns the current decision evaluation.

### 15.2 Get decision history
**GET** `/api/v2/positions/{positionId}/decisions`

Returns decision snapshots and ledger entries.

### 15.3 Get decision ledger
**GET** `/api/v2/positions/{positionId}/ledger`

Returns all ledger records for the position.

### 15.4 Get portfolio health
**GET** `/api/v2/portfolios/{portfolioId}/health`

Returns counts by decision state and health metrics.

### 15.5 Get decision distribution
**GET** `/api/v2/portfolios/{portfolioId}/decision-distribution`

Returns the distribution of holdings across the ladder.

### 15.6 Subscribe to transitions
**POST** `/api/v2/notifications/subscriptions`

Registers notification targets for state changes.

***

## 16. Notification engine

### Rule
Only notify on state changes.

### Notification examples
- DIVIS moved HOLD → ADD
- POLYCAB moved HOLD → ALERT
- GRANULES moved ALERT → STRUCTURE
- PGEL moved STRUCTURE → QUIT

### Notification payload
- symbol
- previousState
- newState
- reason
- triggeredRules
- confidence
- stability
- expiry
- timestamp

***

## 17. Portfolio dashboard

### Required widgets
- Decision distribution widget.
- Portfolio health score.
- State transition feed.
- Holdings table with decision ladder columns.
- Ledger trend chart.
- “At risk” holdings list.

### Holdings table columns
- Symbol
- Current Price
- MRI Score
- CAI Score
- Decision
- Confidence
- Stability
- Expiry
- Next Tranche
- Why
- Why Not Add?
- Portfolio %
- Sector %

***

## 18. Decision ledger module

The decision ledger is a first-class module, not an audit afterthought.

### Purpose
- Improve CAI over time.
- Support backtesting.
- Enable analysis of rule effectiveness.
- Create training data for future ML or tuning.
- Preserve the full decision lineage.

### Ledger row format
| Date | Decision | Price | Rule Score | Confidence | Result |
|---|---|---:|---:|---:|---:|
| 1 Aug | ADD | ₹7,250 | 9/10 | 96% | +18% |
| 22 Aug | HOLD | ₹8,050 | 8/10 | 93% | +23% |
| 12 Sep | ALERT | ₹8,420 | 6/10 | 78% | +17% |
| 26 Sep | QUIT | ₹7,980 | 2/10 | 91% | +11% |

***

## 19. Rule categories

Each rule must belong to one category.

### Categories
- Technical
- Fundamental
- Capital Allocation
- Risk
- Portfolio
- Market

### Why this matters
- Improves explanation quality.
- Makes debugging easier.
- Helps users understand which domain drove the decision.
- Supports better analytics on rule performance.

***

## 20. Decision reasoning requirements

### For every state output, include:
- Why this state.
- Why not the stronger state.
- Triggered rules.
- Rule satisfaction score.
- Stability.
- Expiry.
- Threshold reasons.
- Confidence.

### For non-ADD states, include:
**Why Not Add?**

Examples:
- Breakout not confirmed.
- Volume weak.
- Better MRI candidate exists.
- Already at max portfolio weight.
- Market regime not supportive.

***

## 21. Engineering architecture

### Services
- Market data ingestion service
- MRI evaluation service
- Decision engine service
- Threshold computation service
- Notification service
- Portfolio aggregation service
- Decision ledger service
- Audit/explainability service

### Flow
Market data → feature extraction → MRI inputs → rule evaluation → hierarchy resolution → snapshot creation → ledger write → transition detection → notification dispatch → dashboard refresh

### Important constraints
- Deterministic output for the same input snapshot.
- Idempotent notifications.
- Persistent history.
- No conflicting active states.

***

## 22. Acceptance criteria

The feature is complete when:

1. Every position has exactly one active decision state.
2. The hierarchy resolves conflicts deterministically.
3. Thresholds are separate from states.
4. Each threshold has confidence and reason.
5. Event triggers and price triggers are both supported.
6. Every decision includes triggered rules and rule satisfaction.
7. Every non-ADD output can answer “Why Not Add?”
8. Every decision has a stability score.
9. Every decision has a validity window.
10. The decision ledger stores all historical records.
11. Notifications fire only when the state changes.
12. Portfolio dashboard shows distribution by ladder state.
13. History supports learning and backtesting.

***

## 23. Implementation phases

### Phase 1
- Finalize state model.
- Finalize hierarchy.
- Finalize schemas.

### Phase 2
- Build decision engine.
- Build thresholds and trigger model.
- Build explanation payloads.

### Phase 3
- Build ledger and transition tracking.
- Build notification system.
- Build portfolio aggregation.

### Phase 4
- Add dashboard UI.
- Add analytics.
- Tune rules using ledger outcomes.

***

## 24. AI team prompt

> Build CAI Decision Ladder V2.1 as a portfolio decision operating system.  
> Model decision states separately from thresholds and triggers.  
> Use a deterministic hierarchy: QUIT, then STRUCTURE / PROTECT, then ADD, then HOLD.  
> Produce one canonical decision state per position with confidence, stability, expiry, rule satisfaction, reasons, and triggered rules.  
> Support both price triggers and event triggers.  
> Include a “Why Not Add?” explanation for every non-ADD outcome.  
> Persist a first-class decision ledger and only notify users when state changes.  
> Build portfolio-level aggregation and dashboard widgets for decision distribution and health.


# Execution Plan: CAI Decision Framework V4.0

> **The CAI Decision Framework is a deterministic decision system. Given identical inputs, engine versions, rule versions, policy versions, and market data, it must always produce identical outputs. Every decision must be reproducible, explainable, versioned, and auditable.**

This execution plan operationalizes the **CAI Decision Framework & Decision Ladder (Version 4.0)**. 
Implementation is organized by **risk**—validating the core deterministic computational logic and stability *before* surfacing data via APIs, UIs, or human-readable text.

## Core Developer Rules
1. **Pure Function Interfaces**: Every engine must expose a pure function interface (e.g., `DecisionEngine.evaluate(evaluation, thresholds, rules, policy)`). No database, HTTP, UI, or logging inside core evaluation blocks. The logic must be strictly `Input -> Output`.
2. **Immutable Rule Registry**: After calibration, rule versions are frozen (e.g., `Version 1.0`). Never edit historical rules. Instead, deprecate the old rule and version a new one.
3. **Correctness Over Speed**: Do not optimize for speed until deterministic correctness is proven. Correctness matters infinitely more than performance.
4. **Backward Compatibility**: Every engine must support historical versions (e.g., Rule Registry V1 -> V2) without corrupting historical decisions.
5. **Freeze Public Contracts Early**: Decision Schema, Threshold Schema, Ledger Schema, and Rule Registry Schema must be frozen before Phase 4. These are platform contracts.

## Engineering Quality Standards
- **Rule Coverage Reports**: Every release must output a rule coverage report (e.g., Rules: 132, Executed: 132, Tested: 132, Covered: 100%).
- **Architecture Decision Records (ADRs)**: Every significant architectural decision must be recorded for historical context.
- **Canary Portfolio**: Maintain a fixed "canary portfolio" (e.g., 20 specific stocks) running in CI. If outputs change unexpectedly, the build fails.

---

## The MVDP (Minimum Viable Decision Platform)

### Phase 1: Platform Foundations
*Establishes the core data structures and contracts.*
- **Database migrations**: Create the `decision_history` append-only ledger and related tables.
- **Domain models**: Typed structures for the decoupled pipeline.
- **Strategy profiles**: Define mappings (Momentum, Growth, Conservative).
- **Market regime enum**: (Bull, Bear, Sideways, Risk-On, Risk-Off).
- **Rule registry & Decision registry**: Centralized definitions.
- **Versioning framework**: Ensure `engine_version_data` and schemas track perfectly.
**Definition of Done**: Schemas are finalized, domain models compile, and the database migrations run successfully on a clean database.

### Phase 2A: Market Intelligence
*Compute the raw market understanding.*
- Market Structure Engine
- Position Evaluation Engine
- Decision Threshold Engine
**Definition of Done**: 100% of supported holdings correctly generate standard Market Understanding objects; zero database/HTTP dependencies inside the engines; >95% unit test coverage.

### Phase 2B: Decision Intelligence
*Evaluate market intelligence against the strategy to make decisions.*
- Decision Rule Engine
- Portfolio Policy Engine
- CAI Decision Engine
**Definition of Done**: Decision Engine evaluates 100% of supported holdings into valid Portfolio Decisions; all rule IDs are traceable; deterministic replay passes natively.

### Phase 3: Validation & Replay
*Prove financial correctness before exposing anything to users.*
- Deterministic replay testing.
- Golden scenarios (conflicting indicators, etc.).
- Transition validation.
- Emergency transition tests (e.g., Catastrophic Gap-down).
**Definition of Done**: CI pipeline runs all golden scenarios and emergency transitions continuously; zero false positives on invalid transitions.

### Phase 3.5: Engine Calibration (Mandatory)
*Tune the engine using historical data to ensure sanity and encode investing philosophy.*
- Run the engine against previous trades/historical portfolios.
- Compare recommendations with what actually happened.
- Tune thresholds, rules, and priorities to ensure standard distributions (preventing 42 ADDs out of 100 stocks).
- Freeze rule versions once calibrated.
**Definition of Done**: Rule distributions match historical manual decisions; Rule Registry Version 1.0 is formally frozen.

---

## Post-MVDP Expansion

### Phase 3.75: Simulation Phase (Shadow Mode)
*Run the engine in shadow mode for 30–60 days.*
- Generate decisions every day but do not show them to users.
- Compare decisions against manual decisions.
- Investigate disagreements and capture subtle edge cases.
**Definition of Done**: 30 consecutive days of zero unexplained deviations from the expected deterministic output.

### Phase 4: APIs
*Expose the engine only after it is trusted.*
- Evaluation API
- Ledger API
- Portfolio Health API
- Threshold API
**Definition of Done**: Endpoints successfully serve all frontend payload requirements with strict validation.

### Phase 5: UI & Decision Ladder
*Surface the structured data.*
- Portfolio Dashboard (Health widget, Decision distribution).
- Decision Ladder (Vertical UI hierarchy against price thresholds).
- Holdings Table.
- Fractal Overlay.
**Definition of Done**: Users can view the current state and ledger seamlessly; UI components gracefully handle stale data.

### Phase 6: Explanation Layer
*Add the intelligence and presentation narrative (No business logic here).*
- **Explanation Service**: Consume the structured JSON and output the human narrative.
- **Assistant Panel**: Renders "Why?", "Why Now?", and "What Next?".
- **Traceability Modal**: Show exact passed/failed rules and policy overrides.
**Definition of Done**: Every decision state reliably generates fluent, localized text output explaining the rationale.

### Phase 7: Observability
*Track and monitor engine performance, drift, and investment outcomes over time.*
- **Technical Metrics**: Rule firing frequency, policy override frequency, state transition frequency, average evaluation time, decision drift.
- **Business Metrics**: Average return after ADD, HOLD, ALERT, STRUCTURE, and QUIT decisions to ensure CAI improves outcomes.
**Definition of Done**: Dashboards/alerts are live for both latency and standard business KPIs.

### Phase 8: Decision Analytics
*Improve CAI based on evidence rather than intuition.*
- Which rules fire most often?
- Which rules produce the best outcomes?
- Which policy overrides improve returns?
- Which decision states outperform?
- Which thresholds are too conservative/aggressive?
**Definition of Done**: End-of-month automated reports highlighting rule efficacy and suggested threshold tuning.

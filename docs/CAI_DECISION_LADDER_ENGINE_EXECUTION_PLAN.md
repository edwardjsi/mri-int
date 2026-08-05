# Execution Plan: CAI Decision Ladder Engine V2.0

**Status:** Approved (Frozen V1.0)
**Version:** 1.0
**Owner:** CAI
**Last Updated:** 05 Aug 2026

*Note: This document defines the implementation plan only. It does not define the Decision Ladder algorithm. The algorithm is specified separately in: `docs/DECISION_LADDER_ALGORITHM_V2.md`*

**Reference:** `docs/investor/01 Aug 26 TechAlone.md`

This execution plan operationalizes the strictly scoped, deterministic Decision Ladder Engine. It enforces the anti-hallucination directives (no text narratives, backend-owned states, no probabilistic scores).

---

## Architectural Principles

1. **Backend is the Single Source of Truth:**
   * All Decision Ladder calculations are performed in Python.
2. **React is Presentation Only:**
   * The frontend performs zero business logic and only renders backend-provided values.
3. **Deterministic Engine:**
   * Identical technical inputs must always produce identical outputs.
4. **Technical Data Only:**
   * Version 2.0 uses MRI technical inputs exclusively.
   * No MOSI, fundamentals, AI narratives, or probabilistic adjustments.
5. **Weekly Evaluation:**
   * Decision Ladder values are generated once per week after Friday market close and remain valid until the next scheduled calculation.
6. **Rule Ownership:**
   * The Decision Ladder algorithm is owned by the backend. The database stores its outputs, the API transports them, and the frontend renders them. No layer may redefine or reinterpret the algorithm.

---

## Performance Requirements

* **Batch Performance Target:** The engine shall complete a full portfolio calculation within an acceptable batch-processing window.
  * *Target:* 500 holdings in < 30 seconds.
* **Fault Tolerance:** The engine shall process holdings independently. A failure (or missing data) for one holding must not abort the remaining batch.

---

## Versioning & Standards

* **Decision Ladder Algorithm Version:**
  ```python
  DECISION_LADDER_ALGORITHM = "DL-2.0"
  ```
* **Decision States (ENUM):**
  * `ADD`
  * `HOLD`
  * `ALERT`
  * `STRUCTURE`
  * `QUIT`
  * `NOT_COMPUTED`

---

### Data Flow
```text
Friday Close
      │
      ▼
MRI Technical Data
      │
      ▼
Decision Ladder Engine (DL-2.0)
      │
      ▼
cai_position
      │
      ▼
/api/cai/portfolio
      │
      ▼
React UI (Presentation Only)
```

---

## Phase 1: Database Infrastructure
* **Task:** Create migration script to alter the `cai_position` table.
* **Details:** 
  - Add columns to `cai_position`: `add_level`, `alert_level`, `structure_level`, `quit_level` (all DECIMAL), `decision_state` (ENUM: `ADD`, `HOLD`, `ALERT`, `STRUCTURE`, `QUIT`, `NOT_COMPUTED`), `decision_calculated_at` (TIMESTAMP), and `decision_algorithm_version` (VARCHAR).
  - This keeps the position state unified (avoiding unnecessary JOINs) and provides a flat persistence layer for the current ladder.

## Phase 2: Core Engine Logic (`engine_core/cai_decision_ladder_engine.py`)
* **Task:** Implement the stateless batch engine.
* **Details:**
  - **Input:** Query the existing MRI technical tables to extract all technical inputs required by the approved Decision Ladder algorithm for all active CAI positions.
  - **Algorithm:** Compute the four deterministic thresholds using the approved Decision Ladder algorithm. The engine must be deterministic: identical technical inputs must always produce identical outputs. 
  - **State Calculation:** The backend must explicitly determine the `decision_state` (e.g. `ADD`, `HOLD`, `ALERT`, `STRUCTURE`, `QUIT`).
  - **Summary Output:** Print a standard terminal execution summary upon successful execution:
    ```text
    Algorithm : DL-2.0
    Processed : <Count> positions
    ADD       : <Count>
    HOLD      : <Count>
    ALERT     : <Count>
    STRUCTURE : <Count>
    QUIT      : <Count>
    NOT_COMPUTED : <Count>
    Completed Successfully
    ```

## Phase 3: API Contract Update (`api/cai_portfolio_service.py`)
* **Task:** Update the `/cai/portfolio` endpoint.
* **Details:** 
  - The API response payload remains flat. Return `add_level`, `alert_level`, `structure_level`, `quit_level`, and the computed `decision_state` alongside the symbol. 
  - Do not unnecessarily nest these inside a sub-object.

## Phase 4: UI Refactor & Dumb Rendering Constraint
* **Task:** Refactor `CaiV2Dashboard.tsx` and `StockDecisionPage.tsx`.
* **Details:**
  - Consume the flat payload from the API.
  - **Presentation Only:** React performs zero business logic. It reads `decision_state` directly from the backend and paints the corresponding colors.
  - Display `NOT_COMPUTED` only when the backend has not yet generated a Decision Ladder for the position, ensuring the UI doesn't crash if a batch fails.
  - **UI Validation Constraints:**
    - Test empty state inputs (`workspace.state = {}` and `workspace.state = null`) to ensure rendering resilience.
    - Validate fallback when a position returns `NOT_COMPUTED`.

## Phase 5: Engine Validation
* **Task:** Add deterministic test suite.
* **Details:**
  - Ensure idempotency: run 1 -> levels -> run 2 -> identical levels (with the same weekly inputs).
  - Test edge cases: missing EMA, missing swing low, IPOs, suspended stock, and missing weekly candles to save enormous debugging time later.

## Phase 6: Cron Job Hook
* **Task:** Add execution hook to the existing weekly bash scripts.
* **Details:** Schedule `cai_decision_ladder_engine.py` to run seamlessly in the Friday `17:00` batch process immediately after technical data ingestion.

## Phase 7: Definition of Done
The sprint is complete only when all of the following are true:
* ✅ Every active `cai_position` has computed Decision Ladder values.
* ✅ `decision_state` is persisted for every position.
* ✅ `/cai/portfolio` returns the new fields without breaking existing consumers.
* ✅ React renders the Decision Ladder with zero business logic.
* ✅ `NOT_COMPUTED` appears only for genuinely unavailable backend data.
* ✅ The engine is deterministic (identical inputs → identical outputs).
* ✅ The Friday batch updates all positions successfully.
* ✅ Existing CAI functionality continues to work without regression.

---

## Phase 8: Product Owner Verification

| Test Layer | Method / Command | Expected Result |
| :--- | :--- | :--- |
| **Database** | Query `cai_position` | `add_level`, `alert_level`, `structure_level`, `quit_level`, `decision_state`, and `decision_algorithm_version` ('DL-2.0') columns are correctly populated. |
| **Engine** | Run batch manually `python engine_core/cai_decision_ladder_engine.py` | Summary printed with algorithm version 'DL-2.0', counts for each state, and `Completed Successfully`. |
| **API** | `GET /cai/portfolio` | Flat response payload containing `decision_state`, `add_level`, `alert_level`, `structure_level`, and `quit_level` values. |
| **React UI** | Open portfolio page | Displays decision states and exact numeric thresholds directly from the backend payload with zero UI business calculations. |
| **Determinism** | Run engine twice | Output database state, API responses, and UI elements remain 100% identical. |
| **Formulas** | Manual spot-checks (e.g. `DIVISLAB`) | Spot-check EMA20, EMA50, swing high, swing low values in database against TradingView indicators to verify formula accuracy. |
| **Cron Hook** | Friday Batch run | Ingest technical data and verify engine runs automatically once per week. |

---

## Future Tools: Developer / Debug Truth Table Page
Introduce a hidden debug page in CAI for development and verification that displays the raw input-output mapping for any selected symbol:
* **Inputs:** Current Price, EMA20, EMA50, Swing High, Swing Low
* **Outputs:** Add Level, Alert Level, Structure Level, Quit Level
* **Metadata:** Decision State, Algorithm Version (`DL-2.0`), Calculation Timestamp
This serves as a visual truth table to bypass database query tracing during batch troubleshooting or future algorithm version upgrades.

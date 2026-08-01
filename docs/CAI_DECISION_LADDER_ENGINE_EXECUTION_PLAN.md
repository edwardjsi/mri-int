# Execution Plan: CAI Decision Ladder Engine V2.0

**Reference:** `docs/investor/01 Aug 26 TechAlone.md`

This execution plan operationalizes the strictly scoped, deterministic Decision Ladder Engine. It enforces the anti-hallucination directives (no text narratives, backend-owned states, no probabilistic scores).

## Phase 1: Database Infrastructure
* **Task:** Create migration script to alter the `cai_position` table.
* **Details:** 
  - Add columns to `cai_position`: `add_level`, `alert_level`, `structure_level`, `quit_level` (all DECIMAL), `decision_state` (ENUM: ADD, HOLD, ALERT, STRUCTURE, QUIT, NOT_COMPUTED), `decision_calculated_at` (TIMESTAMP), and `decision_algorithm_version` (VARCHAR).
  - This keeps the position state unified (avoiding unnecessary JOINs) and provides a flat persistence layer for the current ladder.

## Phase 2: Core Engine Logic (`engine_core/cai_decision_ladder_engine.py`)
* **Task:** Implement the stateless batch engine.
* **Details:**
  - **Input:** Query the existing MRI technical tables to extract all technical inputs required by the approved Decision Ladder algorithm for all active CAI positions.
  - **Algorithm:** Compute the four deterministic thresholds using the approved Decision Ladder algorithm. The engine must be deterministic: identical technical inputs must always produce identical outputs. 
  - **State Calculation:** The backend must explicitly determine the `decision_state` (e.g., `ADD`, `HOLD`/`MAINTAIN`, `ALERT`, `STRUCTURE`, `QUIT`).
  - **Output:** Update the existing `cai_position` row. No text generation, no confidence scoring.

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

# Execution Plan: CAI Decision Ladder Engine V2.0

**Reference:** `docs/investor/01 Aug 26 TechAlone.md`

This execution plan operationalizes the strictly scoped, deterministic Decision Ladder Engine. It enforces the anti-hallucination directives (no text narratives, backend-owned states, no probabilistic scores).

## Phase 1: Database Infrastructure
* **Task:** Create migration script to alter the `cai_position` table.
* **Details:** 
  - Add columns to `cai_position`: `add_level`, `alert_level`, `structure_level`, `quit_level` (all DECIMAL), `cai_state` (VARCHAR), and `decision_calculated_at` (TIMESTAMP).
  - This keeps the position state unified (avoiding unnecessary JOINs) and provides a flat persistence layer for the current ladder.

## Phase 2: Core Engine Logic (`engine_core/cai_decision_ladder_engine.py`)
* **Task:** Implement the stateless batch engine.
* **Details:**
  - **Input:** Query the existing MRI technical tables to extract the 12 specified data points (`weekly_close`, `ema_50_w`, `swing_low`, etc.) for all active CAI positions.
  - **Algorithm:** Compute the four deterministic thresholds using the approved Decision Ladder algorithm. 
  - **State Calculation:** The backend must explicitly determine the `cai_state` (e.g., `ADD`, `HOLD`/`MAINTAIN`, `ALERT`, `STRUCTURE`, `QUIT`).
  - **Output:** Update the existing `cai_position` row. No text generation, no confidence scoring.

## Phase 3: API Contract Update (`api/cai_portfolio_service.py`)
* **Task:** Update the `/cai/portfolio` endpoint.
* **Details:** 
  - The API response payload remains flat. Return `add_level`, `alert_level`, `structure_level`, `quit_level`, and the computed `cai_state` alongside the symbol. 
  - Do not unnecessarily nest these inside a sub-object.

## Phase 4: UI Refactor & Dumb Rendering Constraint
* **Task:** Refactor `CaiV2Dashboard.tsx` and `StockDecisionPage.tsx`.
* **Details:**
  - Consume the flat payload from the API.
  - **Presentation Only:** React performs zero business logic. It reads `cai_state` directly from the backend and paints the corresponding colors.
  - Display `NOT_COMPUTED` only when the backend has not yet generated a Decision Ladder for the position, ensuring the UI doesn't crash if a batch fails.

## Phase 5: Engine Validation
* **Task:** Add deterministic test suite.
* **Details:**
  - Ensure idempotency: run 1 -> levels -> run 2 -> identical levels (with the same weekly inputs).
  - Test edge cases: missing EMA, missing swing low, IPOs, suspended stock, and missing weekly candles to save enormous debugging time later.

## Phase 6: Cron Job Hook
* **Task:** Add execution hook to the existing weekly bash scripts.
* **Details:** Schedule `cai_decision_ladder_engine.py` to run seamlessly in the Friday `17:00` batch process immediately after technical data ingestion.

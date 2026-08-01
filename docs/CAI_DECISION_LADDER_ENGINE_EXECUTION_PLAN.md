# Execution Plan: CAI Decision Ladder Engine V2.0

**Reference:** `docs/investor/01 Aug 26 TechAlone.md`

This execution plan operationalizes the strictly scoped, deterministic Decision Ladder Engine microservice. It enforces the anti-hallucination directives (no text narratives, no "Hold" backend levels, no probabilistic scores).

## Phase 1: Database Infrastructure
* **Task:** Create migration script for `cai_decision_ladder` table.
* **Details:** 
  - Fields: `holding_id` (PK/FK to `cai_position.id`), `add_level`, `alert_level`, `structure_level`, `quit_level` (all DECIMAL), and `calculated_at` (TIMESTAMP).
  - Enforce strict `NOT NULL` constraints to guarantee data integrity.

## Phase 2: Core Engine Microservice (`engine_core/cai_decision_ladder_engine.py`)
* **Task:** Implement the stateless batch processor.
* **Details:**
  - **Input:** Query the existing MRI technical tables to extract the 12 specified data points (`weekly_close`, `ema_50_w`, `swing_low`, etc.) for all active CAI positions.
  - **Algorithm:** Compute the four numerical thresholds (`add`, `alert`, `structure`, `quit`) deterministically based on the technical rules (e.g., Alert = 50-EMA proximity, Quit = Swing Low break).
  - **Output:** Perform an UPSERT into `cai_decision_ladder`. No text generation, no confidence scoring.

## Phase 3: API Contract Update (`api/cai_portfolio_service.py`)
* **Task:** Update the `/cai/portfolio` endpoint.
* **Details:** 
  - `LEFT JOIN` the `cai_position` table with `cai_decision_ladder`.
  - Format the response to append the strictly nested `decision_ladder` JSON object to each holding. Remove any legacy narrative/text fields from this endpoint.

## Phase 4: UI Refactor & Dumb Rendering Constraint
* **Task:** Refactor `CaiV2Dashboard.tsx` and `StockDecisionPage.tsx`.
* **Details:**
  - Parse the nested `decision_ladder` object.
  - Implement the **Client-Side "Hold" Calculation:** `IF current_price >= alert_level AND current_price < add_level THEN render(HOLD)` (or equivalent states based on the spec).
  - Remove all fallback `NOT_COMPUTED` logic once the engine is wired, enforcing a strict mapping.

## Phase 5: Cron Job Hook
* **Task:** Add execution hook to the existing weekly bash scripts.
* **Details:** Schedule `cai_decision_ladder_engine.py` to run seamlessly in the Friday `17:00` batch process immediately after technical data ingestion.

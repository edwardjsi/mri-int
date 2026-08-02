# CANSLIM Hybrid Screener & Knowledge Engine Specification

## 1. Objective
To build a highly efficient, deterministic CANSLIM screening module that natively consumes the MRI Indicator Engine and the Company Knowledge Service. 

**Core Architectural Tenets:**
1. **Shared Investment Intelligence Platform:** CANSLIM is not a separate subsystem. It is merely the *first investment model* built on top of a shared technical database and a shared Company Knowledge Service. 
2. **LLM Extracts Facts, Rules Make Decisions:** The AI solely extracts canonical observations (e.g., `OBS-SEM-001: New Product Launch`). A deterministic **Knowledge Rule Engine** evaluates those facts to issue verified evidence, which the CANSLIM Model then consumes.
3. **Evidentiary Grounding:** Every qualitative score is backed by the exact rule executed, the canonical observations found, and an exact string quote.
4. **Caching & Policy-Based Freshness:** Enrichment is only triggered if a stock is missing knowledge or if the knowledge violates the `knowledge_freshness_policy`.
5. **Decoupled Ranking:** The CANSLIM Model produces component verdicts. The central **Portfolio Ranking Engine** handles the actual ranking of stocks based on those verdicts.

---

## 2. The Deterministic Funnel Architecture

### Phase 1: The Quant Filter (Growth, Momentum, Quality, Market)
The CANSLIM model queries the existing MRI Database to evaluate quantitative rules. It does not think in "letters" internally; it evaluates primitives.

*   **Current Earnings & Annual Growth (Growth/Quality)**: 
    *   *Consumer*: Existing Fundamental Quality Verdict schema (`revenue_score`, `margin_score`).
    *   *Rule*: Combined Fundamental Score > 60%.
*   **Volume Expansion (Momentum/Demand)**: 
    *   *Consumer*: MRI Engine Technicals.
    *   *Rule*: `volume_surge` >= 1.3x avg OR Accumulation Velocity (EMA 200 Slope) > 0.
*   **Relative Strength (Leadership)**: 
    *   *Consumer*: MRI Engine Technicals.
    *   *Rule*: Positive 90-day Relative Strength and Price within 15% of 6-month high.
*   **Market Regime (Market)**: 
    *   *Consumer*: Market Regime Engine.
    *   *Rule*: Fails dynamically if the broader market regime is explicitly RISK-OFF.

### Phase 2: The Company Knowledge Service & Refresh Queue (Catalyst, Institutional)
For candidates that pass the Quant Filter, the system queries the **Company Knowledge Service** via the **Knowledge Cache**.

1.  **Check Freshness (`knowledge_freshness_policy`)**: 
    *   Quarterly Knowledge: 120 days.
    *   News: 7 days.
    *   *Result*: If valid, pass facts to the Knowledge Rule Engine. If NO / STALE, place in the **Knowledge Refresh Queue**.
2.  **The Extraction Task**:
    *   If refresh is triggered, the LLM extracts canonical observations (e.g., `OBS-SEM-001: New Product`).
3.  **The Knowledge Rule Engine Evaluation**:
    *   Evaluates rules (e.g., `RULE-KNW-014: Has New Product Catalyst`) based on observations.
    *   Passes the verified `Evidence Store` payload to the CANSLIM Model.

---

## 3. Data Flow & Schema

### The API Flow
```
                    MRI Database
                         |
              Company Knowledge Service
                         |
                  Knowledge Cache
                         |
               Knowledge Rule Engine
                         |
                    Evidence Store
                         |
          +--------------+--------------+
          |                             |
     CANSLIM Model               Future Models
   (consumer only)          (Minervini, Piotrosski)
          |
    Component Verdicts
          |
 Portfolio Ranking Engine
          |
          UI
```

### The Output Schema
```json
{
   "symbol": "GRANULES",
   "knowledge_age_days": 18,
   "compiler_version": "v1.2",
   "components": {
       "Catalyst": {
           "status": "PASS",
           "observations": [
               "OBS-SEM-001",
               "OBS-SEM-002"
           ],
           "rules": [
               "RULE-KNW-014"
           ],
           "extraction_version": "1.2",
           "evidence": [
               "Commissioned Block 4 API Plant"
           ]
       },
       "Institutional": {
           "status": "NOT_APPLICABLE",
           "observations": [],
           "rules": [],
           "extraction_version": "1.2",
           "evidence": []
       }
   }
}
```

---

## 4. Frontend UI/UX (`CanslimScreener.tsx`)

1. **The Screener Grid**: Maps the internal component verdicts (Growth, Leadership, Catalyst, etc.) to the visual **C-A-N-S-L-I-M** letters for the user.
2. **Metadata Columns**: 
    *   `Knowledge Freshness` (e.g., `18 days`)
    *   `Compiler Version`
3. **Status Indicators**:
    *   🟢 `PASS`
    *   🔴 `FAIL`
    *   ⚪ `UNKNOWN` (No data)
    *   🟡 `STALE` (Violates freshness policy)
    *   🔵 `ENRICHING` (Currently in Refresh Queue)
    *   ➖ `NOT_APPLICABLE`
4. **Evidence Tooltips**: Hovering over a `PASS` reveals the `observations`, `rules`, and exact string `evidence`.
5. **The Knowledge Refresh Queue**: A button to "Refresh Unknown/Stale Knowledge".

---

## 5. Deployment Phasing
*   **Sprint 1**: 
    *   Build the CANSLIM Model to consume existing MRI DB metrics and evaluate the Quant components.
    *   Build the UI grid mapping primitives to C-A-N-S-L-I-M.
    *   **Create Golden Regression Dataset:** (e.g., GRANULES expects C: PASS, A: PASS, N: UNKNOWN, etc.). Assert this passes on every commit.
*   **Sprint 2**: Integrate the Company Knowledge Service, Knowledge Cache, and Knowledge Rule Engine to evaluate Catalysts and Institutional.
*   **Sprint 3**: Implement the Knowledge Refresh Queue to auto-trigger the LLM fact-extractor.

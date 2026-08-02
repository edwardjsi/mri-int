# CANSLIM Hybrid Screener & Knowledge Engine Specification

## 1. Objective
To build a highly efficient, deterministic CANSLIM screening module that natively consumes the MRI Indicator Engine and the Company Knowledge Service. 

**Core Architectural Tenets:**
1. **Shared Investment Intelligence Platform:** CANSLIM is not a separate subsystem. It is a downstream consumer of the MRI Database and the Company Knowledge Service. The knowledge is extracted once and consumed by any future model (CANSLIM, Minervini, etc.).
2. **LLM Extracts Facts, Rules Make Decisions:** The AI never decides if a stock "passes" CANSLIM. It solely extracts canonical observations (e.g., `OBS-SEM-001: New Product Launch`). A deterministic CANSLIM Rule Library evaluates those facts to issue a component verdict.
3. **Evidentiary Grounding:** Every qualitative score is backed by an `evidence` count and a verifiable `grounding` status, replacing subjective LLM confidence scores.
4. **Caching & Policy-Based Freshness:** Enrichment is only triggered if a stock is missing knowledge or if the knowledge violates the `knowledge_freshness_policy`.
5. **Decoupled Ranking:** CANSLIM produces evidence and a component verdict. The central Portfolio Ranking Engine handles the actual ranking of stocks.

---

## 2. The Deterministic Funnel Architecture

### Phase 1: The Quant Filter (C, A, S, L, M)
The CANSLIM filter queries the existing MRI Database to evaluate quantitative rules. 

*   **Current Earnings (C) & Annual Growth (A)**: 
    *   *Consumer*: Existing Fundamental Quality Verdict schema (`revenue_score`, `margin_score`).
    *   *Rule*: Combined Fundamental Score > 60%.
*   **Volume Expansion (S)**: 
    *   *Consumer*: MRI Engine Technicals.
    *   *Rule*: `volume_surge` >= 1.3x avg OR Accumulation Velocity (EMA 200 Slope) > 0.
*   **Relative Strength (L)**: 
    *   *Consumer*: MRI Engine Technicals.
    *   *Rule*: Positive 90-day Relative Strength and Price within 15% of 6-month high.
*   **Market Regime (M)**: 
    *   *Consumer*: Market Regime Engine.
    *   *Rule*: Fails dynamically if the broader market regime is explicitly RISK-OFF.

### Phase 2: The Company Knowledge Service & Refresh Queue (N, I)
For candidates that pass the Quant Filter, the system queries the **Company Knowledge Service** via the **Knowledge Cache**.

1.  **Check Freshness (`knowledge_freshness_policy`)**: 
    *   Quarterly Knowledge: 120 days.
    *   News: 7 days.
    *   Concall: 90 days.
    *   Management: 365 days.
    *   *Result*: If valid, pass facts to the CANSLIM Rule Library. If NO / STALE, flag as `UNKNOWN` or `STALE` and place in the **Knowledge Refresh Queue**.
2.  **The Extraction Task**:
    *   If refresh is triggered, the LLM extracts canonical observations (e.g., `OBS-SEM-001: New Product`, `OBS-SEM-002: Capacity Expansion`).
3.  **The CANSLIM Rule Evaluation**:
    *   **New Catalysts (N) [Rule CAN-001]**: Consumes `OBS-SEM-001`, `OBS-SEM-002`, `OBS-SEM-003`. IF count > 0 -> PASS.
    *   **Institutional Buying (I) [Rule CAN-002]**: Consumes `OBS-FIN-001`. IF holding increased -> PASS.

---

## 3. Data Flow & Schema

### The API Flow
```
Indicator Engine -> MRI Database 
                         |
                 CANSLIM Quant Filter 
                         |
             Company Knowledge Service
                         |
                  Knowledge Cache
                         |
                 Missing or Stale?
                /                 \
              YES                  NO
              |                     |
     Knowledge Refresh Queue        |
              |                     |
          MOSI Store <--------------+
              |
      CANSLIM Rule Library
              |
       CANSLIM Evidence
              |
  Portfolio Ranking Engine
```

### The Output Schema
```json
{
   "symbol": "GRANULES",
   "knowledge_age_days": 18,
   "compiler_version": "v1.2",
   "components": {
       "N": {
           "status": "PASS",
           "evidence_count": 2,
           "grounding": "VERIFIED",
           "extraction_version": "1.2",
           "evidence": [
               "We commissioned Block 4 API plant in Q1."
           ]
       },
       "I": {
           "status": "NOT_APPLICABLE",
           "evidence_count": 0,
           "grounding": "NONE",
           "extraction_version": "1.2",
           "evidence": []
       }
   }
}
```

---

## 4. Frontend UI/UX (`CanslimScreener.tsx`)

1. **The Screener Grid**: Displays the CANSLIM component verdicts. Ranking is handled globally by the Portfolio Ranking Engine.
2. **Metadata Columns**: 
    *   `Knowledge Freshness` (e.g., `18 days`, `No Knowledge`)
    *   `Compiler Version` (e.g., `v1.2`)
3. **Status Indicators**:
    *   🟢 `PASS`
    *   🔴 `FAIL`
    *   ⚪ `UNKNOWN` (No data)
    *   🟡 `STALE` (Violates freshness policy)
    *   🔵 `ENRICHING` (Currently in Refresh Queue)
    *   ➖ `NOT_APPLICABLE` (Metric not meaningful for this entity)
4. **Evidence Tooltips**: Hovering over a `PASS` reveals the exact string evidence and extraction provenance.
5. **The Knowledge Refresh Queue**: A button to "Refresh Unknown/Stale Knowledge" which fires the LLM specifically for rows lacking fresh qualitative data.

---

## 5. Deployment Phasing
*   **Sprint 1**: Build the CANSLIM Rule Library to consume existing MRI DB metrics and evaluate the Quant components (C, A, S, L, M). Build the UI grid.
*   **Sprint 2**: Integrate the Company Knowledge Service and Cache to evaluate N and I based on existing stored canonical observations.
*   **Sprint 3**: Implement the Knowledge Refresh Queue to auto-trigger the LLM fact-extractor for missing/stale knowledge.

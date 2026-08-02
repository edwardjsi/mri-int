# CANSLIM Hybrid Screener & Knowledge Engine Specification

## 1. Objective
To build a highly efficient, deterministic CANSLIM screening module that natively consumes the MRI Indicator Engine and MOSI Company Knowledge base. 

**Core Architectural Tenets:**
1. **LLM Extracts Facts, Rules Make Decisions:** The AI never decides if a stock "passes" CANSLIM. It solely extracts structured observations (e.g., *capacity expansion announced*). A deterministic Rule Engine evaluates those facts to issue a Pass/Fail.
2. **Calculate Once, Consume Many Times:** CANSLIM is not a separate subsystem. It is a downstream consumer of the MRI Database and the MOSI Knowledge Store. 
3. **Evidentiary Grounding:** Every qualitative score is backed by a `confidence` rating and an exact `evidence` quote.
4. **Caching & Freshness:** Enrichment is only triggered if a stock is missing knowledge or if the knowledge is mathematically stale.

---

## 2. The Deterministic Funnel Architecture

### Phase 1: The Quant Filter (C, A, S, L, M)
The CANSLIM filter queries the existing MRI Database to evaluate quantitative rules. It does not think in "letters" internally; it evaluates primitives and maps them to the UI.

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

### Phase 2: The Knowledge Lookup & Enrichment Queue (N, I)
For candidates that pass the Quant Filter, the system queries the **MOSI Knowledge Store**.

1.  **Check Freshness**: Is there a MOSI artifact for this symbol? Is it less than 30 days old?
    *   *YES*: Pass facts to the Rule Engine immediately.
    *   *NO / STALE*: Flag as `UNKNOWN` or `STALE` and place in the Enrichment Queue.
2.  **The Extraction Task (Not Decision Task)**:
    *   If enrichment is triggered, the LLM is prompted strictly to extract facts: *"Extract JSON arrays of any new products, capacity expansions, management changes, and institutional holdings changes."*
3.  **The Rule Engine Evaluation**:
    *   **New Catalysts (N)**: *Rule*: IF `len(new_products) > 0` OR `management_change == true` -> PASS.
    *   **Institutional Buying (I)**: *Rule*: IF `institutional_holding_change > 0` -> PASS.

---

## 3. Data Flow & Schema

### The API Flow
```
Indicator Engine -> MRI Database -> CANSLIM Quant Filter -> Candidate List
                                                                 |
                                                          Knowledge Lookup
                                                                 |
                                                         Missing or Stale?
                                                        /                 \
                                                      YES                  NO
                                                      |                     |
                                                LLM Extraction              |
                                                      |                     |
                                                MOSI Store <----------------+
                                                      |
                                              CANSLIM Rule Engine
                                                      |
                                             Ranked Candidate List
```

### The Output Schema
Instead of a simple PASS/FAIL, the API returns a structured score, granular statuses, and evidence.

```json
{
   "symbol": "GRANULES",
   "canslim_score": 87,
   "knowledge_age_days": 18,
   "components": {
       "N": {
           "status": "PASS",
           "confidence": 0.94,
           "evidence": [
               "We commissioned Block 4 API plant in Q1."
           ]
       },
       "I": {
           "status": "STALE",
           "confidence": null,
           "evidence": []
       }
   }
}
```

---

## 4. Frontend UI/UX (`CanslimScreener.tsx`)

1. **The Ranking Grid**: Stocks are sorted by their overall **CANSLIM Score (0-100)** rather than just a binary filter.
2. **Knowledge Freshness Column**: Displays the age of the underlying MOSI artifact (e.g., `18 days`, `No Knowledge`).
3. **Status Indicators**:
    *   🟢 `PASS`
    *   🔴 `FAIL`
    *   ⚪ `UNKNOWN` (No data)
    *   🟡 `STALE` (Data > 30 days old)
    *   🔵 `ENRICHING` (Currently running LLM extraction)
4. **Evidence Tooltips**: Hovering over any `PASS` status in the N or I columns reveals the exact string evidence that triggered the Rule Engine.
5. **The Enrichment Queue**: A button to "Enrich Unknown/Stale Candidates" which fires the LLM specifically for rows lacking fresh qualitative data.

---

## 5. Deployment Phasing
*   **Sprint 1**: Build the Backend Rule Engine to consume existing MRI DB metrics and evaluate the Quant components (C, A, S, L, M). Build the UI grid.
*   **Sprint 2**: Integrate the MOSI Knowledge lookup to evaluate N and I based on existing stored JSON facts.
*   **Sprint 3**: Implement the Enrichment Queue to auto-trigger the LLM fact-extractor for missing/stale knowledge.

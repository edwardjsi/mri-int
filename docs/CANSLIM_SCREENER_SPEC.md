# CANSLIM Hybrid Screener & Enrichment Specification

## 1. Objective
To build a highly efficient CANSLIM screening module that avoids the prohibitive cost and false-negatives of processing the entire market through an LLM. It achieves this by splitting the William O'Neil CANSLIM framework into two distinct phases: a **Strict Quantitative Filter** followed by an **On-Demand LLM Enrichment** for missing qualitative data.

---

## 2. The Two-Phase Funnel Architecture

### Phase 1: The Quant Filter (C, A, S, L, M)
The backend will query the existing PostreSQL database to filter the Nifty 500 down to a manageable shortlist of highly probable candidates (e.g., 20-30 stocks).

*   **[C] Current Earnings & [A] Annual Growth**: 
    *   *Source*: Existing Fundamental Quality Verdict schema (`revenue_score`, `margin_score`).
    *   *Filter*: Must have an aggregate fundamental score > 60%.
*   **[S] Supply and Demand**: 
    *   *Source*: MRI Engine Technicals.
    *   *Filter*: Must show a `volume_surge` (>= 1.3x avg) OR a positive EMA 200 Slope (Accumulation Velocity).
*   **[L] Leader or Laggard**: 
    *   *Source*: MRI Engine Technicals.
    *   *Filter*: Must have positive 90-day Relative Strength (`relative_strength > 0`) and be within 15% of a 52-week or 6-month high.
*   **[M] Market Direction**: 
    *   *Source*: Market Regime Engine.
    *   *Filter*: Screener dynamic weighting adjusts based on Risk-On (Aggressive) vs. Risk-Off (Defensive).

### Phase 2: LLM Enrichment (N, I)
For the 20-30 stocks that survive Phase 1, the system will look up their CIW/MOSI artifacts for "New Products" and "Institutional Sponsorship". If this data is thin or missing, the user triggers an LLM Enrichment task.

*   **[N] New Products / Management / Highs**: 
    *   *Enrichment*: LLM specifically parses recent earnings transcripts/news for "Catalysts", "Capacity Expansions", and "Management Changes".
*   **[I] Institutional Sponsorship**: 
    *   *Enrichment*: LLM extracts mentions of QIB (Qualified Institutional Buyer) accumulation, promoter buying, or block deals.

---

## 3. Data Flow & Endpoints

### 3.1. `GET /api/v1/canslim/screen`
*   **Action**: Executes the SQL filters for Phase 1.
*   **Response**: Returns the top 30 quant-screened stocks.
*   **Schema**:
    ```json
    {
       "symbol": "TCS",
       "quant_score": 85,
       "canslim_status": {
           "C": "Pass", "A": "Pass", "S": "Pass", "L": "Pass", "M": "Pass",
           "N": "Pending_Enrichment",
           "I": "Pending_Enrichment"
       }
    }
    ```

### 3.2. `POST /api/v1/canslim/enrich`
*   **Action**: Takes a list of symbols and triggers the LLM Agent.
*   **Payload**: `{"symbols": ["TCS", "GRANULES"]}`
*   **Process**:
    1. Fetches raw text/transcripts for the symbol.
    2. Prompts LLM: *"Identify major new product launches (N) and institutional buying activity (I) for [Symbol]. Return strict JSON."*
    3. Updates the `mosi_compiled_artifacts` database with the new findings.
*   **Response**: Enriched qualitative data for the UI.

---

## 4. Frontend UI/UX (`CanslimScreener.tsx`)

1. **The Grid**: A clean data-table showing the shortlisted stocks. Columns represent the C-A-N-S-L-I-M letters. 
2. **Visual Indicators**: Letters that pass are highlighted in **Green**. Letters that fail are **Red**. Letters lacking data are **Gray (Pending)**.
3. **The "Auto-Enrich" Button**: A primary action button at the top of the screener: *"Enrich Missing Data (LLM)"*. Clicking this fires the `POST /enrich` endpoint and displays a loading skeleton on the Gray columns until the LLM returns the verified text.
4. **Evidence Tooltips**: Hovering over the enriched "N" or "I" columns will display the exact LLM-extracted quote proving the new product or institutional buy.

---

## 5. Deployment Phasing
*   **Sprint 1**: Build the Phase 1 backend route (`/screen`) utilizing existing database fields, and construct the basic `CanslimScreener.tsx` UI.
*   **Sprint 2**: Build the LLM Enrichment Agent (`/enrich`) and integrate the "Auto-Enrich" frontend workflow.

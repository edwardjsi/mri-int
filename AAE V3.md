# Product Requirements Document (PRD)

# Active Alpha Engine (AAE) — Institutional PE Rerating Detection Platform

## Version: 3.0

## Objective:

Identify high-probability PE rerating candidates **before institutional consensus forms** by detecting the convergence of:

* structural business improvement,
* narrative evolution,
* ownership accumulation,
* and valuation asymmetry.

---

# 1. Executive Summary

AAE is an institutional-grade equity intelligence platform designed to detect:

```text id="7rq9e4"
early-stage market rerating conditions
```

rather than merely:

```text id="5njov4"
good businesses.
```

The engine combines:

* structured financial analysis,
* AI-assisted narrative intelligence,
* ownership/market confirmation,
* valuation asymmetry detection,
* governance risk filtering,
* and anti-pattern learning.

The platform is NOT:

* an automated trading system,
* a prediction engine,
* or a fully autonomous AI investor.

AAE is:

> a probabilistic institutional research and conviction engine.

Human sign-off remains mandatory.

---

# 2. Core Strategic Objective

The system must identify companies where:

```text id="0s2dpc"
institutional perception is likely to improve
BEFORE
valuation expansion fully occurs.
```

The engine seeks to detect:

* PE rerating,
* EV/EBITDA expansion,
* quality reclassification,
* institutional accumulation,
* and narrative transition.

---

# 3. Core Design Philosophy

## Four-Layer Institutional Confirmation Framework

A candidate qualifies ONLY when multiple orthogonal dimensions align.

| Layer                  | Objective                                        |
| ---------------------- | ------------------------------------------------ |
| Financial Confirmation | Is the business structurally improving?          |
| Narrative Confirmation | Has management communication evolved materially? |
| Ownership Confirmation | Is smart money accumulating?                     |
| Valuation Confirmation | Is the rerating still underpriced?               |

---

# 4. System Architecture

```text id="15u7u8"
                ┌─────────────────────────┐
                │  MARKET UNIVERSE        │
                └────────────┬────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │ Governance + Liquidity   │
              │ Hard Filters             │
              └────────────┬─────────────┘
                           │
                           ▼
         ┌────────────────────────────────┐
         │ Layer 1 — Financial Inflection │
         └────────────────┬───────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ Layer 2 — Narrative Evolution  │
         └────────────────┬───────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ Layer 3 — Ownership & Market   │
         └────────────────┬───────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │ Layer 4 — Valuation Asymmetry  │
         └────────────────┬───────────────┘
                          │
                          ▼
             ┌────────────────────────┐
             │ Expected Rerating Score│
             └────────────────────────┘
```

---

# 5. Restricted Universe Rules

## Universe Constraints

The engine shall operate ONLY on:

* Nifty 500
* liquid midcaps
* institutional-grade smallcaps

---

## Liquidity Filters

Reject if:

```python id="a4qgwm"
avg_daily_traded_value < ₹10Cr
market_cap < ₹1500Cr
delivery_ratio < 25%
```

---

# 6. Governance Kill Switch Layer

## Hard Exclusion Conditions

Immediate rejection if ANY condition is true:

| Condition                             | Threshold |
| ------------------------------------- | --------- |
| Promoter pledge ratio                 | >25%      |
| Auditor resignation                   | TRUE      |
| Qualified audit opinion               | TRUE      |
| Sudden CFO resignation                | TRUE      |
| Repeated equity dilution              | TRUE      |
| High related-party transaction growth | TRUE      |

---

## Governance Database Schema

```sql id="v9c8q1"
CREATE TABLE aae_governance_metrics (
    symbol TEXT,
    fiscal_year INT,
    fiscal_quarter INT,
    promoter_holding_pct NUMERIC,
    pledged_shares_pct NUMERIC,
    auditor_flag BOOLEAN,
    cfo_exit_flag BOOLEAN,
    related_party_risk BOOLEAN,
    governance_score NUMERIC
);
```

---

# 7. Sector-Specific Modeling Engine

## Objective

Avoid generic cross-sector analysis.

---

## Mandatory Sector Engines

```python id="l2xz7s"
sector_models = {
  "BANKS": BankEngine(),
  "NBFC": NBFCEngine(),
  "EMS": EMSEngine(),
  "CDMO": CDMOEngine(),
  "CHEMICAL": ChemicalEngine(),
  "CONSUMER": ConsumerEngine(),
  "AUTO_ANC": AutoAncillaryEngine()
}
```

Each sector engine shall:

* use sector-specific metrics,
* use sector-specific scoring,
* normalize against sector medians.

---

# 8. Financial Inflection Engine

## Objective

Estimate:

```text id="2m0suv"
Probability of Structural Business Improvement
```

---

# 9. Financial Metrics

## Profitability Metrics

* EBITDA margin trend
* gross margin trend
* operating leverage
* ROCE expansion

---

## Cash Conversion Metrics

* CFO/PAT ratio
* receivable days
* inventory days
* FCF conversion

---

## Balance Sheet Metrics

* debt reduction
* leverage stability
* capex efficiency
* working capital efficiency

---

# 10. Structural vs Cyclical Separation

## Objective

Avoid cyclical false positives.

---

## Initial Implementation (Simplified)

Use:

* sector-relative normalization
* commodity correlation overlays
* persistence scoring
* rolling margin stability

---

## Example Logic

```python id="rntulz"
if company_margin_expansion
AND industry_margin_expansion:
    structural_confidence -= 40%
```

---

# 11. Advanced State-Space Filtering (Phase 2)

## Future Upgrade

Introduce:

* Kalman filtering,
* latent structural trend estimation,
* cyclical decomposition.

---

## Mathematical Framework

```text id="9lcg9i"
Observed Margin = Structural Trend + Cyclical Component
```

---

# 12. Probabilistic Scoring System

## Replace Binary Triggers

Old:

```python id="g9k0ow"
if all_conditions_met:
    trigger
```

New:

```python id="gkhg0q"
rerating_probability = weighted_probabilistic_model()
```

---

# 13. Financial Inflection Score

```python id="2xjlwm"
financial_score =
(
  margin_quality * 0.30 +
  roce_trend * 0.25 +
  cash_conversion * 0.25 +
  balance_sheet_strength * 0.20
)
```

---

# 14. Narrative Evolution Engine

## Objective

Detect:

```text id="v3ebps"
material evolution in management communication
```

NOT generic sentiment.

---

# 15. Narrative AI Capabilities

## Detect:

* strategic progression
* increasing specificity
* timeline evolution
* narrative escalation
* narrative deterioration

---

## Example

```text id="g3qt7l"
Q1: evaluating
Q2: approved
Q3: commissioning
Q4: scaling
```

---

# 16. Narrative-Numeric Divergence Engine

## Objective

Detect contradiction between:

* management language,
* and business reality.

---

## Example

```python id="u7duz2"
if optimism_up
AND cash_conversion_down:
    credibility_score -= severe_penalty
```

---

# 17. Speaker-Weighted Transcript Intelligence

## Prioritize:

* CFO Q&A
* analyst questioning
* unscripted commentary

---

## Discount:

* prepared remarks
* boilerplate optimism

---

## Transcript Weighting

```python id="jlwmx9"
weights = {
  "CFO_QA": 1.5,
  "ANALYST_QA": 1.3,
  "CEO_PREPARED": 0.5
}
```

---

# 18. Theme Saturation Engine

## Objective

Measure narrative crowding.

---

## Example

If:

* 80 companies mention “AI”
* 50 mention “exports”

then:

```python id="w9z4iw"
theme_uniqueness_score decreases
```

---

# 19. Ownership & Market Confirmation Engine

## Objective

Confirm institutional accumulation.

---

# 20. Ownership Metrics

Track:

* FII accumulation
* DII accumulation
* mutual fund additions
* insider buying/selling
* promoter holding changes
* pledge changes

---

# 21. Market Confirmation Metrics

Track:

* relative strength
* volume expansion
* delivery expansion
* volatility contraction
* breakout preparation

---

# 22. Market Divergence Logic

## Critical Rule

If:

* fundamentals improve,
* but price remains persistently weak,

then:

```python id="v8n4nm"
market_confirmation_penalty += large
```

---

# 23. Valuation Asymmetry Engine

## Objective

Detect:

```text id="jq9r4d"
high-quality businesses where rerating is NOT fully priced in.
```

---

# 24. Valuation Metrics

Track:

* rolling PE percentile
* EV/EBITDA percentile
* PEG ratio
* sector premium/discount
* historical valuation range

---

# 25. Opportunity Classification

| Category                   | Meaning        |
| -------------------------- | -------------- |
| Great business + ignored   | Elite          |
| Improving business + cheap | High asymmetry |
| Great business + euphoric  | Dangerous      |
| Weak business + expensive  | Avoid          |

---

# 26. Expected Rerating Engine

## Master Composite Score

```python id="j2dnpm"
expected_rerating_score =
(
  financial_inflection * 0.35 +
  narrative_evolution * 0.20 +
  ownership_confirmation * 0.25 +
  valuation_asymmetry * 0.20
)
```

---

# 27. Score Interpretation

| Score | Meaning                          |
| ----- | -------------------------------- |
| 80+   | Institutional rerating candidate |
| 65-79 | Emerging rerating setup          |
| 50-64 | Monitor closely                  |
| <50   | Noise / insufficient convergence |

---

# 28. False Positive Graveyard

## Objective

Systematically learn from failed setups.

---

# 29. Failure Database

```sql id="pwprw3"
CREATE TABLE aae_false_positive_graveyard (
    symbol TEXT,
    failure_type TEXT,
    failure_reason TEXT,
    rerating_score NUMERIC,
    post_failure_return NUMERIC,
    lessons JSONB
);
```

---

# 30. Failure Categories

Track:

* cyclical traps
* governance implosions
* narrative pumps
* multiple compression
* fake breakouts
* accounting distortions

---

# 31. AI Usage Policy

## AI SHALL:

* compare documents
* detect semantic shifts
* detect contradictions
* track management evolution
* extract governance signals
* monitor narrative saturation

---

## AI SHALL NOT:

* autonomously trade
* predict prices
* generate unrestricted bull theses
* override governance filters
* replace human judgment

---

# 32. Human-in-the-Loop Framework

## AI Role

```text id="n8c7rw"
Institutional research analyst
```

---

## Human Role

```text id="wl2vg6"
Portfolio manager and capital allocator
```

Humans remain responsible for:

* conviction,
* position sizing,
* portfolio construction,
* macro judgment,
* and risk management.

---

# 33. Data Sources

## Structured Data

* NSE/BSE filings
* quarterly financials
* shareholding patterns
* screener.in
* company IR pages

---

## Unstructured Data

* earnings call transcripts
* investor presentations
* annual reports
* conference call Q&A

---

# 34. Technology Stack

| Layer                | Technology       |
| -------------------- | ---------------- |
| Database             | PostgreSQL       |
| Backend              | Python           |
| AI Extraction        | GPT-4o-mini      |
| Final Synthesis      | GPT-4o           |
| Financial Processing | Pandas / NumPy   |
| APIs                 | NSE/BSE/yfinance |
| Frontend             | Next.js          |
| Visualization        | Recharts         |

---

# 35. AI Architecture Principles

## Retrieval Before Reasoning

Always:

```text id="1zw7xb"
retrieve evidence
→ compare deltas
→ generate constrained inference
```

Never:

```text id="2m8gpk"
free-form AI thesis generation
```

---

# 36. Operational Stop Rules

## DO NOT:

* auto-execute trades
* scan illiquid microcaps
* use unrestricted agentic workflows
* overfit historical winners
* deploy massive vector infrastructure prematurely

---

# 37. Success Metrics

## System Success =

Ability to identify companies:

* before institutional accumulation peaks,
* before valuation expansion completes,
* while governance remains healthy,
* and while narrative evolution is still underappreciated.

---

# 38. Final Strategic Definition

AAE is NOT:

```text id="ndqj3v"
a stock prediction engine.
```

AAE IS:

```text id="9wmt4q"
an institutional rerating detection framework
designed to identify early perception change
before valuation fully reprices.
```

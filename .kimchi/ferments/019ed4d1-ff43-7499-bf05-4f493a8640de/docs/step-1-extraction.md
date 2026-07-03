# Step 1 Extraction — MRI Marketing Plan Source Material

Three source documents read. Themes extracted below. All quotes verbatim with file:line citations.

---

## Source 1: docs/AAE_PRD.md

### Theme A — Product Vision

**Long-term vision:** AAE (Amritkaal Alpha Engine) is described as an "event-driven, multi-agent research and stock-selection platform for Indian listed equities" whose primary output is "a ranked list of re-rating candidates, continuously updated company theses, and risk dashboards for professional investor review."

The stated goals:
- "Detect structural business inflections before consensus recognition."
- "Map qualitative change to financial fingerprints and valuation re-rating probability."
- "Maintain living theses with source evidence, score history, and risk state."
- "Surface thesis breaks quickly through risk dashboards and alerts."
- "Preserve human sign-off; AAE is an analyst decision-support system, not an execution engine."

The core differentiator: most systems find "good businesses." AAE finds **re-rating conditions** — structural inflection points before the market prices them in. This framing is the most exportable for marketing.

**Target users (explicitly named):**
- "Buy-side analysts and portfolio managers focused on Indian equities."
- "Family offices and HNIs running concentrated portfolios."
- "Quant and hybrid funds that want machine-generated ideas with human review."

**V1 Non-Goals (important for positioning — what MRI is NOT):**
- No automated order execution.
- No high-frequency or intraday trading.
- No global equities; V1 focuses on Indian NSE/BSE listed equities.
- No unsupported LLM-only investment conclusions.

### Theme B — Positioning Language

No standalone tagline found in AAE_PRD.md. The positioning language comes through the feature descriptions and architecture. Key phrases for marketing:

- "event-driven, multi-agent research and stock-selection platform" (line 3)
- "decision-support system, not an execution engine" (line 28)
- "Every output references source documents or data points. Deterministic pipelines where possible. LLM randomness constrained." (Non-Functional Requirements)
- "Output language must remain research and decision-support oriented." (Security and Compliance)

The six structural signals are named and marketable:
1. Margin Quality
2. TAM Expansion
3. Backward Integration
4. Forward Integration
5. Moat Strengthening
6. Geographic Expansion

The Master Investor Checklist is referenced as the base quality scoring framework.

### Theme C — Advisor-Facing Features

**Technical modules:**

1. **Re-Rating Candidate Profile** (per company + as-of date): structural signal vector, structural conviction score, financial fingerprint metrics, Master Investor Checklist score, operating leverage classification, capital efficiency metrics, macro alignment score, risk state, valuation vs. history and peers, re-rating probability score 0–100, thesis object with evidence and version history.

2. **Structural Signal Agent** — maps qualitative events to the six structural signals with conviction scores 0–100. Generates high-conviction structural alerts when at least 4 of 6 signals fire within 12–18 months.

3. **Financial Fingerprint Agent** — validates qualitative claims against quantitative time series:
   - Sales CAGR (3yr, 5yr), EBITDA CAGR, PAT CAGR
   - Degree of Operating Leverage (DOL)
   - Gross and EBITDA margin trend
   - ROCE and ROE trend
   - FCF/PAT and cash conversion
   - Working capital metrics (receivables, inventory, payables, cash conversion cycle)
   - Capex intensity, debt, interest coverage, leverage
   - Valuation vs. history and peers

4. **Macro Correlation Agent** — sector macro tailwind/headwind score, market valuation regime estimate, sector relative attractiveness, company-level macro alignment score.

5. **Execution Monitoring Agent / Risk Dashboard** — financial strain (EBIT/interest, net debt/EBITDA), earnings quality (FCF/PAT deterioration, non-cash earnings), working capital flags, governance red flags (auditor resignations, pledges, related-party anomalies), margin compression tracking. Outputs: risk dashboard (green/amber/red) + "thesis-at-risk" label + alert stream with source evidence.

6. **Sector Lens** — sector heat map separating structural from cyclical stories, top re-rating candidates per sector, policy/macro/demand/flow/valuation context.

7. **Thesis Object** — a living document with structural driver summary, financial corroboration, macro context, risk state, valuation context. Analyst can Accept/Reject/Modify/Override with notes.

**Operational features:**

- **Event-driven ingestion** — new filings, transcripts, presentations, announcements trigger re-analysis within 5–15 minutes.
- **Watchlists and alerts** with configurable severity.
- **Analyst console** in React/Vite frontend — dashboard, company page, event view, watchlist/alerts.
- **Email alerts first** (Slack/Teams deferred).

### Theme D — Quantifiable Claims

**Verified/Backtested** (from INVESTOR_DECK_V2.md, Slide 9):
- MRI Strategy CAGR: **26.39%** (5-year walk-forward simulation 2021–2026, including T+1 slippage)
- MRI Strategy Max Drawdown: **-33.53%**
- MRI Strategy Sharpe Ratio: **1.23**
- Nifty 50 Buy & Hold CAGR: ~10.5%, Max Drawdown: -59.60%, Sharpe: 0.42

**Operational/Scale**:
- "Daily screening of 800+ stocks (Nifty 500 + BSE Group A)" — from INVESTOR_DECK_V2.md, Slide 3
- Latency target: "Event to initial analysis target: 5–15 minutes after filing availability" — from AAE_PRD.md, Non-Functional Requirements

**Aspirational/Roadmap**:
- Phase 2 (Global Market Connect — US/EU ingestion): Q3 2026
- Phase 3 (Full-stack API & White-label Research): "The Future"
- Long-term coverage target: "full NSE/BSE coverage" (vs. current curated universe)

No verified AAE-specific performance stats exist yet (AAE is still in Phase 0–1 implementation per the PRD).

### Theme E — Compliance & Framing

The most important compliance language in AAE_PRD.md:

- "Preserve human sign-off; AAE is an analyst decision-support system, not an execution engine." (Goals section, line 28)
- "Output language must remain research and decision-support oriented." (Security and Compliance, Non-Functional Requirements)
- "No automated order execution." (Non-Goals for V1)
- "Read-only market data access." (Security and Compliance)
- "No trading capability in V1." (Security and Compliance)
- Review action labels (Watch, Trim Review, Exit Review, Ignore Noise) "must not be framed as automated trade instructions." (Risk Monitoring use case)
- "Every analyst action must be stored for audit and future calibration." (UX Requirements)

The INVESTOR_DECK_V2.md adds:
- Slide 5: '"Cash is a Position"' — regime-based capital preservation framing
- Slide 9: Performance table with asterisk implies backtested results with slippage modeled

**Gap:** No SEBI-specific compliance language found in AAE_PRD.md. The PRD does not reference SEBI registration categories, RIA frameworks, or investment adviser regulations. This will need to be sourced externally for the marketing plan.

### Theme F — Audience Signals

Explicitly named target users (AAE_PRD.md, Target Users section):
- "Buy-side analysts and portfolio managers focused on Indian equities."
- "Family offices and HNIs running concentrated portfolios."
- "Quant and hybrid funds that want machine-generated ideas with human review."

**Notably absent:** The PRD does NOT explicitly mention "RIAs," "SEBI-registered investment advisers," "wealth managers" (as a distinct category), or "PMS" (portfolio management services). These are implicit but not named.

INVESTOR_DECK_V2.md adds:
- "The Alpha Gap in Emerging Markets" — positions MRI as bridging "the information asymmetry gap between retail markets and institutional quant desks."
- Vision framing: "Bridging the information asymmetry gap between retail markets and institutional quant desks." (Slide 1)
- Phase 3 roadmap targets: "Institutional SaaS (Full-stack API & White-label Research)" — explicitly institutional.

**Key tension:** AAE_PRD.md targets "buy-side analysts, portfolio managers, family offices, HNIs, quant and hybrid funds" — sophisticated principals. But the INVESTOR_DECK frames the ICP as bridging retail-to-institutional quant desks. The marketing plan will need to reconcile whether MRI's primary B2B buyer is the advisor managing client money (RIA/PMS/advisor) or the institutional analyst at a fund. These have different buying triggers and decision processes.

---

## Source 2: docs/investor/INVESTOR_DECK_V2.md

### Theme A — Product Vision

MRI's stated vision: "Bridging the information asymmetry gap between retail markets and institutional quant desks."

Core value proposition: "Detecting structural inflections and PE re-ratings *before* the market prices them in."

The deck frames MRI as solving three structural problems in emerging markets:
1. **Late-Stage Consensus**: "By the time a stock hits retail news, institutional re-rating is 70% complete."
2. **Narrative Blindness**: "Financials are backward-looking; management 'narrative shifts' are buried in thousands of transcript pages."
3. **Volatility Without Guardrails**: "No systematic way to exit before macro drawdowns (The 'Risk-Off' problem)."

The product is framed as a "Full-Stack Ecosystem" with three layers:
- Layer 1: Daily screening of 800+ stocks
- Layer 2: Market Regime classification (Risk-On/Off breadth-based engine)
- Layer 3: AAE V3 (Active Alpha Engine) for PE re-rating detection

### Theme B — Positioning Language

**Tagline (Slide 1):** "Institutional-Grade Alpha & Risk Engine for Indian Equities"

**Sub-vision line:** "Bridging the information asymmetry gap between retail markets and institutional quant desks."

**Core value (Slide 1):** "Detecting structural inflections and PE re-ratings *before* the market prices them in."

**Capital protection philosophy (Slide 5):** "Cash is a Position" — breadth-based regime engine to prevent "buying the dip" in bear markets.

**AAE differentiation (Slide 6):** "Most systems find 'good businesses.' AAE V3 finds **Re-rating Conditions**."

**AAE mechanism (Slide 6):** "80% Deterministic (Quant) + 20% Forensic (AI)."

**Forensic AI framing (Slide 8):** "We use high-leverage AI to audit the 'Management Story': Theme Saturation tracking, Numeric Divergence detection, The Graveyard feedback loop."

**Roadmap vision:** "AI-driven Forensic Research at Quant-Speed."

### Theme C — Advisor-Facing Features

**MRI scoring model (0–100, Slide 4):**

| Factor | Weight | What It Measures |
|---|---|---|
| Trend Integrity | 25% | EMA 50/200 Alignment |
| Trend Slope | 25% | Velocity of institutional accumulation |
| Relative Strength | 20% | Outperformance vs. Nifty 50 Benchmark |
| Price Proximity | 20% | Momentum vs. 6-Month Highs |
| Volume Surge | 10% | Institutional participation confirmation |

**Market Regime Classification (Slide 5):**
- Risk-On: Aggressive signal generation
- Neutral: 85+ score threshold (Flight to Quality)
- Risk-Off: Automated SELL triggers & Capital Preservation

**AAE V3 Four-Layer Institutional Confirmation (Slide 7):**

| Layer | Objective |
|---|---|
| Financial | Structural margin/ROCE inflection detection |
| Narrative (AI) | LLM-driven "Tone Shift" detection in earnings calls |
| Ownership | FII/DII accumulation & Delivery Ratio analysis |
| Valuation | PEG and Rolling PE percentile asymmetry |

**Forensic AI features (Slide 8):**
- Theme Saturation: Tracking new focus areas (e.g., "De-leveraging" or "Export Pivot")
- Numeric Divergence: Catching cases where management tone is bullish but financial delta is flat
- The Graveyard: Feedback loop that learns from past "Value Traps" to refine future filters

**Performance validation (Slide 9):** 5-year walk-forward simulation results (see Theme D).

### Theme D — Quantifiable Claims

**Verified/Backtested** (Slide 9):
- MRI Strategy CAGR: **26.39%** (vs. ~10.5% Nifty 50 B&H) — 5-year walk-forward simulation, including T+1 slippage
- MRI Strategy Max Drawdown: **-33.53%** (vs. -59.60% Nifty 50 B&H)
- MRI Strategy Sharpe Ratio: **1.23** (vs. 0.42 Nifty 50 B&H)

**Scale** (Slide 3):
- "Daily screening of 800+ stocks (Nifty 500 + BSE Group A)"

**Aspirational/Roadmap** (Slide 10):
- Phase 2: Global Market Connect (US/EU Ingestion) — Q3 2026
- Phase 3: Institutional SaaS (Full-stack API & White-label Research)
- "The Future: AI-driven Forensic Research at Quant-Speed"

### Theme E — Compliance & Framing

No explicit compliance disclaimers in the investor deck. The implicit framing is:
- MRI is positioned as a "decision-support" tool for analysts and portfolio managers
- The "Cash is a Position" philosophy and automated SELL triggers in Risk-Off regime are described but framed as part of the scoring system, not trade execution
- The 80/20 deterministic/AI split signals credibility over black-box AI

**Gap:** No SEBI regulatory framing, no investment adviser disclaimer language, no "for professional investors only" explicit language. This needs to be sourced externally.

### Theme F — Audience Signals

**Primary audience:** Institutional-facing, sophisticated investors who understand quant concepts (Sharpe ratio, PEG, rolling PE percentile, FII/DII flows). The investor deck itself is pitched to potential investors/founders.

**Implicit advisor audience (from deck framing):**
- "Buy-side analysts and portfolio managers" — AAE_PRD.md
- "Family offices and HNIs" — AAE_PRD.md
- The deck talks about "bridging retail markets and institutional quant desks" — implying retail investors are NOT the audience, but the gap MRI fills benefits advisors who serve retail clients

**Notable gap:** The deck and PRD are investor-facing (for MRI's own fundraising), not prospect-facing (for MRI selling to advisors). No direct "here's why YOU should buy this" language for a wealth manager or RIA buyer.

---

## Source 3: docs/GUIDANCE_EMAIL_ENHANCEMENT_PLAN_2026-06-17.md

### Theme A — Product Vision

**Not directly relevant.** This is an engineering implementation plan for adding two new UI sections to the GuidanceCheck email. It describes the existing GuidanceCheck feature (management tone monitoring and promise tracking from earnings calls) but does not contain product vision language.

### Theme B — Positioning Language

**Not directly relevant.** No marketing positioning language. The document describes technical implementation of an email mirroring feature.

### Theme C — Advisor-Facing Features

This document is highly relevant because it describes two advisor-facing features in production detail:

**1. Management Tone (Intonation) Monitor — 9 dimensions:**
From `GuidanceCheck.tsx` referenced in the plan, the tone monitor tracks:
1. Confidence
2. Hedging
3. Aggression
4. Transparency
5. Optimism
6. Pessimism
7. Accountability
8. Numerical Density

Plus: headwinds named (by management), tone shift detection (chip), quarter-over-quarter deltas, and tone trajectory over time (last 8 quarters as a table/sparkline).

The tone monitor is described as a "Tone Shift" alert: "🚨 TONE SHIFT" chip fires when the tone shifts meaningfully quarter-over-quarter.

**2. Header Metadata Band (already in payload, missing from email):**
- Transcript count + date range
- Total promises extracted
- Numerical guidance % (with color coding: red <30%, amber <70%, green ≥70%)
- Dominant guidance type
- "DIRECTIONAL ONLY" chip (fires when `guidance_quality_signal == "DIRECTIONAL ONLY"`)

**3. GuidanceCheck / ConvictionEngine — Promise Tracking:**
- Verified promises (✅ Kept, ❌ Broken, ⚠️ Partial)
- Upcoming promises
- "No verified promises yet" fallback (when `total_verified == 0`)
- `integrity_signal`, `quarter_comparison`, `integrity_timeline`

**4. AAE Forensic Audit (mentioned as OUT OF SCOPE for this enhancement):**
The plan explicitly distinguishes the GuidanceCheck email from the AAE forensic audit email (`build_aae_report_email_html`), which has different content: master score, layers, bear/bull case. The AAE report fires from the StockDetailsModal "Run AAE Audit" button.

### Theme D — Quantifiable Claims

**None.** This is an implementation plan with no performance metrics, backtest results, or business KPIs.

### Theme E — Compliance & Framing

**Not directly relevant.** No compliance language. The plan does describe a semantic distinction that has compliance implications:

- The GuidanceCheck tracks management *promises* and their *verification* against actual financials
- The "No verified promises yet" fallback explicitly flags when management "gives directional / qualitative guidance only — they don't typically commit to numbers"
- The "DIRECTIONAL ONLY" chip highlights management teams that lack numeric accountability

These features position MRI as an *accountability tracker*, which is a strong compliance-adjacent selling point: advisors can show clients they tracked management commitments and held them accountable.

### Theme F — Audience Signals

**Not directly relevant.** No explicit audience targeting. However, the features described are clearly advisor-oriented:
- Management tone monitoring from earnings calls — a tool for analysts doing fundamental research
- Promise tracking and integrity scoring — the kind of thing a wealth manager or RIA uses to justify investment decisions to end clients
- The AAE forensic audit distinction suggests the StockDetailsModal is a direct-to-advisor tool

---

## Cross-Source Synthesis

### Top 5 Most Marketable Features/Capabilities, Ranked

1. **PE Re-Rating Detection (AAE/Structural Signals)** — "Most systems find 'good businesses.' AAE V3 finds *Re-rating Conditions*" — this is the single clearest differentiation statement. It targets the advisor's core need: finding the stock BEFORE the re-rating happens.

2. **26.39% CAGR / 1.23 Sharpe / -33.53% Max Drawdown (Backtested)** — The only hard performance number in the deck. With the caveat that these are backtested (not live), they are the most compelling quantified proof point for marketing copy.

3. **Market Regime Risk-Off Engine / "Cash is a Position"** — This solves the "Volatility Without Guardrails" problem. Wealth managers and advisors' biggest client-satisfaction risk is losing money in drawdowns. Regime-based capital preservation is a strong emotional and rational hook.

4. **Management Tone Monitor + Tone Shift Detection (GuidanceCheck)** — The 9-dimension tone tracking and "TONE SHIFT" alert are highly differentiated and explainable to end clients. An advisor can say: "We have an AI that reads every earnings call and tells us when management's tone shifts — before it shows up in the numbers." This is a client-facing story, not just an analyst story.

5. **Master Investor Checklist / Financial Fingerprint (6 Structural Signals + Quantitative Validation)** — The six signals (Margin Quality, TAM Expansion, Backward/Forward Integration, Moat Strengthening, Geographic Expansion) give advisors a structured framework to explain WHY they own a stock. This is client communication gold.

### Top 5 Strongest Verbatim Quotes for Marketing Use

1. **"Most systems find 'good businesses.' AAE V3 finds *Re-rating Conditions*."** — INVESTOR_DECK_V2.md, Slide 6. Best single-line positioning.

2. **"Bridging the information asymmetry gap between retail markets and institutional quant desks."** — INVESTOR_DECK_V2.md, Slide 1. Vision-level tagline.

3. **"Institutional-Grade Alpha & Risk Engine for Indian Equities"** — INVESTOR_DECK_V2.md, Slide 1. Clean, professional tagline.

4. **"By the time a stock hits retail news, institutional re-rating is 70% complete."** — INVESTOR_DECK_V2.md, Slide 2. Best problem-statement hook for an advisor ICP.

5. **"AAE is an analyst decision-support system, not an execution engine."** — AAE_PRD.md, line 28. Critical compliance and positioning framing.

### Gaps: What the Docs DON'T Tell Us

1. **No live performance data.** The 26.39% CAGR is a 5-year backtest. The marketing plan needs live-track record claims (even if partial). We need to know: how long has MRI been running live? What's the live Sharpe since go-live? Without this, we must qualify all performance claims with "backtested" — which weakens the story.

2. **No pricing, packaging, or subscription model.** The marketing plan needs to propose a week-by-week 0→1 playbook for acquiring the first 10 paying advisor subscriptions — but no pricing information exists in the docs. The INVESTOR_DECK mentions "Phase 3: Institutional SaaS (Full-stack API & White-label Research)" but no pricing tiers, trial periods, or onboarding flows.

3. **No SEBI regulatory framing.** The advisor ICP is "SEBI-registered advisors, RIAs, wealth managers" but neither the PRD nor the deck contains SEBI-specific language, compliance disclaimers, or RIA regulatory context. The marketing plan will need to source this externally.

4. **No customer count or social proof.** Zero mentions of how many advisors currently use MRI, what they pay, or testimonials/case studies. This is the biggest gap for a B2B sales playbook. The plan will need to fabricate realistic ICP buyer personas based on the product description and design a first-customer acquisition strategy accordingly.

5. **No ICP buyer decision process data.** The PRD describes what the product does, the deck describes its performance — but neither describes how an advisor or wealth manager actually buys something like MRI. Key questions unanswered:
   - Who signs the purchase order? (Compliance officer? CIO? Founder-RIAs?)
   - What's the evaluation period? (Do they trial on their own portfolio first?)
   - What's the buying trigger? (Losing clients? Regulatory requirement? Competitor using it?)
   - How does MRI integrate into existing workflows? (Standalone tool? Excel add-in? API?)

6. **No email/CRM/outbound infrastructure described.** The 0→1 playbook will need to invent a demand-generation strategy, but the docs don't describe any existing marketing infrastructure, email list, or distribution channels. The daily email digest is mentioned as a product feature, not a marketing channel.

7. **No AAE Phase 1–4 completion status.** AAE_PRD.md describes Phase 0 as "in progress through PRDE" and Phase 1–4 as future deliverables. The marketing plan cannot accurately position AAE features unless the actual build state is confirmed. We don't know which features are shipped, which are in-progress, and which are roadmap.

---

*Extraction complete. Three documents read. Six themes per document. Cross-source synthesis produced. Output: `step-1-extraction.md`.*
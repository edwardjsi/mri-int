# MOSI AI Master Analysis vs MRI Platform (PERX + AAE)

Comparison of the MOSI AI Master Analysis Prompt v2.0 against the MRI Platform's PERX (PE Re-Rating Discovery Engine) and AAE (Alpha Architect Engine) modules.

**Date:** May 29, 2026

---

## Overview

MOSI is a **14-step institutional PE expansion / multi-bagger detection prompt** — designed as a single deep-dive framework to run on one company at a time with uploaded documents (annual reports, transcripts, presentations).

MRI's PERX/AAE modules are an **automated, database-driven platform** that scores hundreds of stocks daily without manual document uploads, combining deterministic financial scoring with AI-powered forensic debate.

---

## Step-by-Step Coverage Map

| # | MOSI Step | MRI Module(s) | Coverage |
|---|-----------|--------------|----------|
| 1 | **Company Stage Classification** (Early / Expansion / Early Maturity / Mature) | `scoring.py::classify_lifecycle_stage()` → Euphoria / Institutional Expansion / Early Rerating / Accumulation / Distribution | Different lens. MOSI uses business lifecycle; MRI uses institutional re-rating phase. Complementary. |
| 2 | **Global Macro Trend** (product parallel, global adoption, India emergence, technology+policy inflection) | `aae_macro_agent.py` | ✅ Covered at concept level |
| 3 | **Government Policy Alignment** (PLI, FAME, NMP, Green Hydrogen, Jal Jeevan, Semiconductor Mission, budget allocation) | — | ❌ Gap. No India-specific policy scheme analysis |
| 4 | **Business Segment Decomposition** (revenue %, 3yr CAGR per segment, primary growth engine, CapEx timeline with traffic-light) | — | ❌ Gap. Yearly aggregate financials only; no segment-level breakdown |
| 5 | **6-Quarter Performance Table** (Revenue, EBITDA, PAT with YoY% per quarter + acceleration flag) | `investor_context.py::get_earnings_momentum()` | ⚠️ Partial. Acceleration/deceleration detection exists, but no formatted 6Q YoY table |
| 6 | **Financial Health Check** (margins, ROE, ROCE, FCF, operating leverage, receivable days, current ratio) | `prde_scoring_engine.py` (8-component Master Investor Checklist) + QIF 7-agent system | ✅ Strong. Operating leverage, capital efficiency, margin quality, growth quality, cash conversion, balance sheet — all scored deterministically |
| 7 | **Balance Sheet Quality** (D/E level & trend, FCF/PAT, current ratio) | `prde_scoring_engine.py::score_balance_sheet_health()` + `get_ev_ebitda()` (net debt/EBITDA) | ✅ D/E level + trend scored. Net debt/EBITDA via EV calc |
| 8 | **Management Quality & Governance** (pledging, audit risk, related party transactions) | `governance_engine.py` (AAE Layer 0 Kill Switch) + `get_ownership_signals()` (promoter trend, pledged %, governance score) | ✅ Kill switch triggers at >25% pledging. Promoter buying/selling trend detected |
| 9 | **Peer Comparison** (Revenue CAGR, OPM, ROCE vs named listed peers — Outperforming/In-line/Underperforming) | `sector.py::get_sector_context()` (MRI rank within sector) + sector median P/E | ⚠️ Partial. Ranks by MRI score and computes sector median P/E. Revenue CAGR/OPM/ROCE peer comparison not implemented |
| 10 | **Management Credibility Check** (CONFIRMED / AHEAD OF NUMBERS / NARRATIVE TRAP) | `engine_guidance/credibility_scorer.py` (GuidanceCheck — built May 28, 2026) | ✅ Exact match. Accuracy %, IMPROVING/STABLE/DETERIORATING trend, leaderboard, thesis tracking |
| 11 | **Valuation Trilogy** (P/E, EV/EBITDA, P/S vs company history, sector peers, global comps) | `get_valuation_context()` (P/E, sector median PE, 5yr historical percentile) + `get_peg_ratio()` + `get_ev_ebitda()` | ✅ P/E, PEG, EV/EBITDA covered. P/S not covered |
| 12 | **Risk Assessment** (probability High/Medium/Low × impact High/Medium/Low matrix) | `compute_fragility_snapshot()` (HIGH/MODERATE/LOW) + `score_risk_penalty()` + PERX pre-mortem risk list | ✅ Fragility classification with reasons. Pre-mortem risk bullets in PERX reports. No probability×impact matrix |
| 13 | **Synthesis & Final Verdict** (✅ Ready / 🟡 Getting Ready / 🔴 Not Ready) | `build_final_verdict()` in PERX + AAE `master_score` (0-100) + PERX institutional suitability tiers | ✅ PERX: Strong/Developing/Early tiers. AAE: REJECTED/ACTIVE status with 10-layer breakdown |
| 14 | **Multi-Bagger Probability Score (0-10)** with dimensional rubric | `prde_scoring_engine.py::compute_master_score()` | ⚠️ Partial. PRDE has 7 weighted dimensions but MOSI's specific rubric (Revenue CAGR 1.5, Margin 1.5, ROCE 1.5, TAM 1.5, Balance Sheet 1, Narrative 1, Stage Cycle 1) is more explicitly multi-bagger-oriented |

### Overall Coverage: ~75%

---

## What MRI has that MOSI doesn't

| MRI-Only Capability | Module | Description |
|---|---|---|
| **Technical Momentum Layer** | `indicator_engine.py` / `signal_generator.py` | 7-step MRI score (EMA 50/200, RS 90d, Volume, Breakout, Price Quality) — 0-100 weighted |
| **STEE Swing Trade Setup** | `scoring.py::compute_stee_setup_score()` | Breakout entry detection, stop loss, 2R exit, position sizing |
| **Trajectory Velocity** | `scoring.py::compute_trajectory_support()` | Score change rate + direction over time |
| **FII/DII Institutional Flow** | `investor_context.py::get_institutional_flow()` | Quarterly FII/DII holding % changes, ADDING/REDUCING/STABLE trends |
| **Liquidity Profile** | `investor_context.py::get_liquidity_profile()` | Average daily turnover (₹Cr), days to build ₹50L position |
| **Historical Re-rating Analogs** | `investor_context.py::get_rerating_analogs()` | Same lifecycle + similar score comparison from archived PERX reports |
| **Investor Grade A/B/C** | `investor_context.py::compute_investor_grade()` | 4-pillar composite: valuation, earnings momentum, ownership, liquidity |
| **Bear vs Bull AI Debate** | `forensic_debate.py` (AAE Layers 9-10) | GPT-4o-mini adversarial stress test — bull case vs bear case with evidence |
| **Narrative Intensity** | `scoring.py::narrative_intensity_label()` | HIGH/MEDIUM/LOW based on PERX score |
| **Narrative-Numeric Divergence** | AAE orchestrator | Flags when management tone is more bullish than financials justify |
| **Daily Automated Pipeline** | `pipeline_cloud.sh` | Scores 500+ stocks daily; MOSI requires manual one-at-a-time execution |
| **Email + PDF Delivery** | `email_service.py` + `pdf_generator.py` | Branded institutional reports delivered automatically |

---

## Architecture Comparison

| Dimension | MOSI AI | MRI Platform |
|-----------|---------|--------------|
| **Execution Model** | Manual, one company at a time | Automated daily pipeline (500+ stocks) |
| **Input** | Uploaded documents (AR, transcripts, presentations) | Database (daily_prices, fundamental_financials, quarterly_financials, governance_metrics) |
| **Scoring** | LLM-based qualitative assessment | ~90% deterministic SQL + ~10% AI (GPT for narrative/debate) |
| **Technical Analysis** | None | Full 7-step MRI momentum scoring |
| **Fundamental Analysis** | Prompt-guided LLM reasoning | Deterministic PRDE 8-component checklist + QIF 7-agent system |
| **Delivery** | Text output in chat | API + React dashboard + branded HTML email + PDF |
| **Cost per Stock** | ~$0.02-0.05 (GPT-4o-mini deep analysis) | ~$0.00015 (GPT extraction only for transcripts) |

---

## Gaps to Close for Full MOSI Parity

1. **Government Policy Analysis Engine** — India scheme alignment (PLI, FAME, NMP, Green Hydrogen, etc.) with budget allocation verification
2. **Business Segment Decomposition** — Would require segment-level revenue/profit data (not available in current data sources)
3. **P/S Ratio** — Simple addition to `get_valuation_context()`
4. **6-Quarter Formatted Table** — Extend `get_earnings_momentum()` to produce the MOSI-style quarterly table with per-quarter YoY%
5. **Peer OPM/ROCE/Revenue CAGR Comparison** — Extend `get_sector_context()` beyond MRI score ranking
6. **Multi-Bagger Probability Rubric** — Layer MOSI's exact 7-dimension scoring (Revenue CAGR, Margin, ROCE, TAM, Balance Sheet, Narrative, Stage Cycle) on top of PRDE as an output label

# PERX + AAE + MOSI Unifier

**Date:** May 29, 2026  
**Branch:** `feature/perx-aae-mosi-unifier`  
**Status:** In Progress

---

## Objective

Bring together PERX (PE Re-Rating Discovery Engine), AAE (Alpha Architect Engine), and GuidanceCheck into a single unified institutional analysis screen. Additionally, close the MOSI AI Master Analysis gaps identified in the comparison audit to achieve ~90%+ feature parity with the MOSI 14-step framework.

**Key constraint:** Compose existing modules — do not rewrite them.

---

## Background

The MRI Platform currently surfaces institutional intelligence across three separate pages:

| Page | What It Does | Frontend | API |
|------|-------------|----------|-----|
| 🏛️ PERX | Re-rating discovery, lifecycle, investor context, sector, analogs | `PerxPage` in `App.tsx` | `POST /api/perx/scan/{symbol}` |
| 🧬 AAE Console | 10-layer forensic audit, governance, narrative, debate | `AaeDashboard.tsx` | `POST /api/aae/scan/{symbol}` |
| 🔍 GuidanceCheck | Management credibility tracking | `GuidanceCheck.tsx` | `GET /api/guidance/*` |

An investor who wants the full picture must switch between three screens. The unifier composes all three engines into one call → one screen.

The [MOSI AI Master Analysis Prompt v2.0](https://mosi.ai) comparison audit (see `MosiVsAAEPERXComparison.md`) identified 6 gaps. Four are practical to close with existing data; two require external data sources and are deferred.

---

## Architecture

```
UnifiedAnalysis.tsx  (new single-screen page)
  ┌──────────┬──────────┬──────────┬────────────┐
  │  Signal  │  PERX    │   AAE    │ Guidance   │
  │  Card    │  Layers  │  Layers  │ Check      │
  └──────────┴──────────┴──────────┴────────────┘
  ┌──────────────────────────────────────────────┐
  │          MOSI Additions Panel                 │
  │  Multi-Bagger | P/S | Quarterly Table | Peers │
  └──────────────────────────────────────────────┘
         │
         ▼
POST /api/unified/scan/{symbol}
         │
         ▼
engine_core/unified_analysis.py  (composer — no rewrites)
         │
         ├─► generate_perx_report()
         ├─► ReRatingOrchestrator.build_profile()
         ├─► CredibilityScorer.compute_score()
         │
         └─► NEW MOSI gap functions:
              compute_multi_bagger_score()
              get_ps_ratio()
              get_formatted_quarterly_table()
              get_peer_fundamental_comparison()
```

---

## Implementation Plan

### Phase 1: MOSI Gap Functions (4 new deterministic functions)

| # | Function | File | MOSI Step | Description |
|---|----------|------|-----------|-------------|
| 1.1 | `get_ps_ratio()` | `engine_perx/investor_context.py` | Step 11 | P/S = Market Cap / TTM Revenue |
| 1.2 | `get_formatted_quarterly_table()` | `engine_perx/investor_context.py` | Step 5 | 6Q table: Revenue/EBITDA/PAT w/ YoY% + accel |
| 1.3 | `get_peer_fundamental_comparison()` | `engine_perx/sector.py` | Step 9 | OPM/ROCE/Rev CAGR vs peers |
| 1.4 | `compute_multi_bagger_score()` | `engine_core/unified_analysis.py` | Step 14 | MOSI 7-dim rubric (0-10) |

### Phase 2: Unified Orchestrator

| # | Task | File | Description |
|---|------|------|-------------|
| 2.1 | Create `UnifiedAnalyzer` class | `engine_core/unified_analysis.py` | Composes PERX + AAE + GuidanceCheck + MOSI gaps |
| 2.2 | Unified report payload schema | `engine_core/unified_analysis.py` | Sections: signal, perx, aae, guidance, mosi_additions |

### Phase 3: Unified API Endpoint

| # | Task | File | Description |
|---|------|------|-------------|
| 3.1 | `POST /api/unified/scan/{symbol}` | `api/unified.py` | FastAPI router calling UnifiedAnalyzer |
| 3.2 | Register router | `api/main.py` | include_router |

### Phase 4: Unified Frontend

| # | Task | File | Description |
|---|------|------|-------------|
| 4.1 | Create `UnifiedAnalysis` component | `frontend/src/UnifiedAnalysis.tsx` | 4-panel single-screen layout |
| 4.2 | Add API method | `frontend/src/api.ts` | `scanUnified(symbol)` |
| 4.3 | Wire navigation | `frontend/src/App.tsx` | Sidebar + mobile nav |

### Phase 5: Verification

| # | Task |
|---|------|
| 5.1 | Test with RELIANCE — all sections populate |
| 5.2 | Test with TCS — guidance + multi-bagger |
| 5.3 | Test error isolation — partial results with warnings |

---

## Deferred (Requires External Data)

| MOSI Step | Description | Blocker |
|-----------|-------------|---------|
| Step 3 | Government Policy Alignment | Requires policy scheme DB or LLM integration |
| Step 4 | Business Segment Decomposition | Requires segment-level revenue data |

---

## MOSI Multi-Bagger Rubric (Step 14)

Scored 0-10 across 7 weighted dimensions:

| Dimension | Full | Half | Zero |
|-----------|------|------|------|
| Revenue growth (1.5) | CAGR >= 25% + latest Q >= 25% | CAGR 15-25% | CAGR < 15% |
| Margin expansion (1.5) | Structural drivers, expanding | Cyclical or stable | Contracting |
| ROCE quality (1.5) | ROCE > 20%, rising | ROCE 15-20%, stable | ROCE < 15% or falling |
| TAM headroom (1.5) | TAM > 10x revenue | TAM 3-10x revenue | TAM < 3x revenue |
| Balance sheet (1) | D/E < 0.25, FCF+, CR > 1 | D/E 0.25-1 | D/E > 1 or FCF neg |
| Narrative (1) | CONFIRMED | Ahead of numbers | Narrative trap |
| Stage cycle (1) | Early or Expansion | Early Maturity | Mature/Ex-growth |

## Unified Report Payload Schema

```json
{
  "symbol": "RELIANCE",
  "signal": {
    "rating": "READY",
    "multi_bagger_probability": 7.5,
    "multi_bagger_breakdown": {}
  },
  "perx": {
    "score": 82.5,
    "lifecycle": "Institutional Expansion",
    "engine_outputs": {},
    "investor_context": {}
  },
  "aae": {
    "master_score": 78.3,
    "layers": {},
    "bull_case": "",
    "bear_case": ""
  },
  "guidance": {
    "accuracy_pct": 72.0,
    "trend": "IMPROVING"
  },
  "mosi_additions": {
    "ps_ratio": 3.2,
    "quarterly_table": [],
    "peer_fundamentals": []
  }
}
```

---

## Git Strategy

- Branch: `feature/perx-aae-mosi-unifier` (from `main`)
- Commit per phase
- Push for testing before merge
- Deferred gaps → separate branches

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-29 | Initial plan. Phase 1-5 defined. Branch created. |

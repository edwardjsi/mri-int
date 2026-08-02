# Milestone M1 — CAI Platform Vertical Slice Validated

**Date:** 2026-08-02
**Status:** ✅ Validated & Frozen

## Goal
To prove the end-to-end viability of the core CAI platform architecture by executing a complete vertical slice—from unstructured research data to a fully explainable, deterministic UI decision tree—without tightly coupling the layers.

## What Was Validated
We successfully demonstrated the following operational pipeline for a single company (GRANULES) and a single rule (`RULE-KNW-001`), confirming the boundaries hold up in code:

```text
Research (MOSI)
        │
        ▼
Compiler
        │
        ▼
Knowledge Artifacts
        │
        ▼
Knowledge Repository
        │
        ▼
Company Knowledge Service
        │
        ▼
Knowledge Evidence Engine
        │
        ▼
Rule Library
        │
        ▼
Evidence
        │
        ▼
Investment Model (CANSLIM)
        │
        ▼
Explainability Framework
        │
        ▼
React UI
```

## Stable Interfaces (Frozen for V1)
The following domain models, services, APIs, and frameworks are now officially frozen. Any modifications to these contracts require explicit approval.

### Domain Models
* `CompanyKnowledge`
* `Fact`
* `Observation`
* `Entity`
* `RuleEvidence`
* `ExplainNode`

### Services
* `CompanyKnowledgeService` (The purely structural knowledge repository)
* `KnowledgeEvidenceService` (The dependency inversion layer for models)

### APIs
* `GET /api/v1/company-knowledge/{symbol}`
* `POST /api/v1/knowledge/evaluate`

### Explainability
* Recursive `ExplainNode` contract
* `DecisionExplanation.tsx` recursive UI component

### Rule Framework
* Base `KnowledgeRule`
* Rule Registry (`registry.py`)
* Rule Versioning (`version = "1.0"`)

## Next Phase: The Pivot to Calibration
The architecture phase is complete. The platform will no longer prioritize net-new infrastructure. Development bandwidth is now reallocated into four core workstreams:

1. **Knowledge:** Improve compiler extraction, entity resolution, and coverage.
2. **Rules:** Scale the deterministic corpus (e.g., `RULE-KNW-002` → `100`).
3. **Calibration:** Track precision, recall, and false positives for all rules.
4. **Models:** Complete CANSLIM, then add Minervini, Piotroski, and proprietary CAI models.

# Company Knowledge Service v1

## Objective
To strictly decouple the investment models (CANSLIM, Minervini, etc.) from the complexities of data extraction (MOSI Compiler, LLMs, PDF parsers). The architecture enforces a rigid pipeline: **Knowledge** is mapped to **Evidence** via rules, and models consume **Evidence**.

---

## The Architecture

```text
                MOSI Compiler
                      │
                      ▼
             Company Knowledge
                      │
          Company Knowledge Service
                      │
                      ▼
           Knowledge Evidence Engine
                      │
                      ▼
                 Evidence Store
          ┌───────────┼───────────┐
          ▼           ▼           ▼
      CANSLIM      Minervini     MRI
          │
          ▼
Portfolio Ranking Engine
```

---

## 1. Knowledge API (Pure Knowledge)

This API acts as the "database" interface for the Company Knowledge Service. It serves structured facts, entities, and observations, completely agnostic to investment models.

**Endpoint:** `GET /api/v1/company-knowledge/{symbol}`

### Response Schema

```json
{
  "symbol": "GRANULES",
  
  "metadata": {
    "knowledge_version": 5,
    "compiler_version": "1.2",
    "knowledge_age_days": 18,
    "last_refresh": "2026-07-15T00:00:00Z",
    "is_stale": false
  },
  
  "facts": [
    {
      "fact_id": "KNW-00442",
      "category": "Management",
      "metric": "Capacity",
      "value": "4000 MTPA",
      "source": "Commissioned Block 4 API Plant..."
    }
  ],

  "entities": [
    {
      "entity_id": "ENT-PLANT-004",
      "name": "Block 4 API Plant",
      "type": "Manufacturing Facility"
    }
  ],

  "observations": [
    {
      "observation_id": "OBS-SEM-001",
      "type": "NEW_PRODUCT",
      "entity_id": "ENT-PLANT-004",
      "value": true,
      "source_fact": "KNW-00442",
      "grounding": "VERIFIED"
    }
  ]
}
```

---

## 2. Knowledge Evidence Engine API (Evidence Generation)

This service evaluates structured knowledge against predefined rules tied to specific models to generate deterministic **Evidence**. Models call this service by declaring their identity, rather than manually passing rules.

**Endpoint:** `POST /api/v1/knowledge/evaluate`

### Request Schema

```json
{
  "symbol": "GRANULES",
  "model": "CANSLIM"
}
```

### Response Schema (Evidence Payload)

```json
{
  "symbol": "GRANULES",
  "evidence": [
    {
      "rule": "RULE-KNW-014",
      "rule_version": "1.0",
      "status": "PASS",
      "observations": [
        "OBS-SEM-001"
      ],
      "quotes": [
        "Commissioned Block 4 API Plant..."
      ]
    }
  ]
}
```

## Architectural Guarantees

1. **Model-Centric Evaluation**: Models do not need to know which rules they require. The Evidence Engine acts as a central registry mapping models (e.g., `CANSLIM`) to their required rule arrays.
2. **Rule Versioning**: Every piece of evidence carries a `rule_version`. Future recalibrations will not silently break historical deterministic tests.
3. **Immutable Observation IDs**: `OBS-SEM-001` is an eternal identifier. Downstream consumers bind to the ID, meaning the human-readable `type` can evolve without breaking the platform.
4. **No Logic Leakage**: The Company Knowledge Service serves raw facts. The Evidence Engine maps facts to Evidence. The CANSLIM Model strictly consumes Evidence.

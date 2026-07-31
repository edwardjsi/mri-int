I like this direction much more. It shifts MRI from being a **hard-coded expert system** to a **self-evolving knowledge system**.

Below is the PRD I would hand to an AI engineering team.

---

# Engineering PRD

# MRI Adaptive Knowledge Extraction Engine (AKE) v1.0

**Status:** Ready for Implementation

**Priority:** P0

**Owner:** Knowledge Platform

---

# 1. Objective

Build a knowledge extraction engine that converts every MOSI report into structured knowledge.

The engine must:

* Extract every possible variable from the report.
* Never discard unknown variables.
* Learn new variables over time.
* Automatically promote recurring variables into the canonical schema.
* Keep the Decision Engine independent from schema evolution.

The system must become smarter with every MOSI report processed.

---

# 2. Design Philosophy

Traditional systems:

```text
Report
↓

Known Fields Only

↓

Discard Unknown
```

MRI:

```text
Report

↓

Extract Everything

↓

Known → Canonical DB

Unknown → Reserve DB

↓

Learn

↓

Promote

↓

Knowledge grows forever
```

---

# 3. Goals

The engine must:

✓ Never lose information

✓ Learn automatically

✓ Version the schema

✓ Maintain backward compatibility

✓ Be deterministic

✓ Be explainable

✓ Be auditable

---

# 4. System Architecture

```text
                    MOSI Report
                          │
                          ▼
                  Document Parser
                          │
                          ▼
                 Universal Extractor
                          │
                          ▼
               Normalized Variable Objects
                          │
                          ▼
                 Variable Registry Engine
               ┌──────────┴──────────┐
               ▼                     ▼
        Canonical Variables    Reserve Variables
               │                     │
               └──────────┬──────────┘
                          ▼
                Promotion Engine
                          │
                          ▼
              Canonical Knowledge Schema
                          │
                          ▼
             Knowledge Update Processor
                          │
                          ▼
                 Company Workspace
                          │
                          ▼
                  Decision Engine
```

---

# 5. Components

## 5.1 Document Parser

Input

```
PDF
Markdown
```

Output

```
Normalized Markdown
```

Use

* MarkItDown

---

## 5.2 Universal Extractor

Purpose

Extract every structured fact from the report.

Not just predefined fields.

Output

```json
[
  {
    "section":"Business Quality",
    "variable":"Pricing Power",
    "value":"High",
    "confidence":0.96
  },
  {
    "section":"Monitoring",
    "variable":"CDMO Revenue",
    "value":"28%",
    "confidence":0.98
  }
]
```

No filtering.

---

## 5.3 Variable Registry

Every extracted variable enters the registry.

Schema

```
VariableID

RawName

CanonicalName

Section

DataType

Confidence

Status

Occurrences

Companies

Aliases

CreatedAt

UpdatedAt
```

Status

```
CANONICAL

RESERVE

MERGED

DEPRECATED
```

---

# 6. Canonical Knowledge Database

Contains only promoted variables.

Example

```
business_quality

management_quality

pricing_power

moat_score

capital_allocation

risks

catalysts

monitoring

thesis

confidence
```

Decision Engine reads only this database.

---

# 7. Reserve Variable Database

Stores every new discovery.

Example

```
Variable

CDMO Revenue
```

Occurrences

```
1
```

Companies

```
Neuland
```

Status

```
RESERVE
```

Nothing is discarded.

---

# 8. Promotion Engine

Runs after every ingestion.

Algorithm

```
If

Occurrences >= Config.MinimumOccurrences

AND

UniqueCompanies >= Config.MinimumCompanies

AND

AverageConfidence >= Config.MinimumConfidence

THEN

Promote
```

Default Configuration

```
MinimumOccurrences = 2

MinimumCompanies = 2

MinimumConfidence = 0.90
```

Configurable.

---

# 9. Alias Detection

Detect semantic duplicates.

Example

```
Top Customer Exposure

Customer Concentration

Largest Client Share
```

AI suggests

```
Merge?
```

User approves.

Registry

```
Canonical

customer_concentration
```

Aliases

```
Top Customer Exposure

Largest Client Share
```

---

# 10. Structured Output

Universal Extractor produces

```json
{
  "company":"NEULAND",

  "variables":[
      {
        "section":"Monitoring",
        "name":"CDMO Revenue",
        "value":"28%",
        "type":"percentage",
        "confidence":0.98
      }
  ]
}
```

Nothing else touches the raw report.

---

# 11. Knowledge Update

Known variables

↓

WorkspaceUpdater

Unknown variables

↓

Reserve

No unknown variable is ignored.

---

# 12. Workspace Update

Canonical variables update

* Thesis
* Risks
* Catalysts
* Monitoring
* Business Quality
* Timeline
* Evidence

Reserve variables do not modify the workspace until promoted.

---

# 13. Schema Evolution

Version every schema.

Example

```
Schema v1.0

145 variables
```

Later

```
Schema v1.1

149 variables
```

Workspace stores

```
Schema Version Used
```

---

# 14. Audit Trail

Every promotion recorded.

Example

```
Variable

CDMO Revenue

First Seen

Neuland

Occurrences

2

Companies

Neuland

Syngene

Promoted

2026-09-11

Promoted By

Automatic
```

---

# 15. APIs

```
POST /extract

POST /ingest

GET /variables

GET /variables/reserve

GET /variables/canonical

POST /variables/promote

POST /variables/merge

POST /variables/reject

GET /schema

GET /schema/history
```

---

# 16. Database Tables

```
SourceDocument

ExtractedVariable

VariableRegistry

VariableAlias

CanonicalVariable

ReserveVariable

PromotionHistory

SchemaVersion
```

---

# 17. Definition of Done

Given a MOSI report,

the system must:

✓ Parse document

✓ Extract every variable

✓ Update known variables

✓ Store unknown variables

✓ Detect recurring variables

✓ Promote qualifying variables

✓ Update schema version

✓ Preserve complete audit history

✓ Never lose extracted information

---

# 18. Future Extensions

The extraction engine must work unchanged for:

* Annual Reports
* Investor Presentations
* Concall Transcripts
* Earnings Call Audio (after transcription)
* Management Interviews
* Exchange Filings
* News Articles

Only the **Document Parser** changes. The extraction, registry, promotion, and workspace update pipeline remains identical.

---

## One enhancement I'd add before implementation

I'd insert a **Human Review Queue** between the Reserve Database and automatic promotion.

Instead of immediately promoting every qualifying variable, the engine creates a **Promotion Candidate**:

```text
CDMO Revenue

Occurrences: 3

Companies:
- Neuland
- Syngene
- Divi's

Suggested Canonical Name:
cdmo_revenue_share

Confidence: 97%

Status:
Awaiting Review
```

A single click ("Approve", "Merge", or "Reject") lets you control the evolution of MRI's ontology while still benefiting from automatic discovery. That keeps the knowledge model high quality without slowing down ingestion. This gives you the best of both worlds: continuous learning with editorial control over what becomes part of the permanent Decision Engine schema.

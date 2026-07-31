I actually think we should renumber them.

The document I just called "Document 4" is actually the document that should have been **Document 0**. It defines the ubiquitous language of the system. Every other document depends on it.

This is the document Eric Evans would write before any database schema or services.

---

# MRI Knowledge OS

# Document 0: Domain Model & Ubiquitous Language

**Status:** P0 Foundation

**Purpose**

This document establishes the vocabulary of MRI. Every PRD, service, API, database table, and UI must use these terms consistently.

---

# Core Philosophy

MRI is **not** a document management system.

MRI is **not** a vector database.

MRI is **not** an LLM wrapper.

MRI is a **Knowledge Operating System for Investing**.

Its purpose is to transform unstructured research into persistent, explainable, evolving investment knowledge.

---

# The Seven Core Domain Objects

## 1. Company

### Definition

A company is the primary entity that MRI tracks.

Everything else ultimately exists because of a company.

Examples

* Divi's Labs
* Neuland
* Polycab

Owns

* Documents
* Knowledge
* Decisions

---

## 2. Source Document

Definition

An immutable piece of research.

Examples

* MOSI Report
* Annual Report
* Investor Presentation
* Credit Rating
* Concall Transcript

Important

A SourceDocument never changes.

If the same report is uploaded again,

a new document version is created.

---

## 3. Fact

Definition

A fact is a single piece of information extracted from one SourceDocument.

Examples

```text
Pricing Power = High

CDMO Revenue = 28%

Customer Concentration = 42%
```

Facts are evidence.

Facts are never manually edited.

Facts are immutable.

---

## 4. Variable

Definition

A Variable is an ontology concept.

It describes **what kind of fact** MRI understands.

Examples

```text
pricing_power

customer_concentration

management_quality
```

Variables do not contain values.

Variables define meaning.

---

## 5. Knowledge

Definition

Knowledge is MRI's current accepted belief about a company.

Example

```text
Company

↓

Pricing Power

↓

High
```

Knowledge is derived.

Knowledge is not extracted.

Knowledge is inferred from evidence.

---

## 6. Decision

Definition

A decision is an action generated from knowledge.

Examples

```text
BUY

ADD

HOLD

EXIT

WATCH
```

A Decision never reads documents.

It only reads Knowledge.

---

## 7. Portfolio

Definition

Portfolio represents the user's capital allocation.

Portfolio never reads documents.

Portfolio never performs AI reasoning.

Portfolio consumes Decisions.

---

# Relationships

```text
Company
    │
    ├── owns Documents
    │
    ├── owns Knowledge
    │
    └── generates Decisions

Document
    │
    └── contains Facts

Fact
    │
    └── classified by Variable

Knowledge
    │
    └── built from Facts

Decision
    │
    └── built from Knowledge

Portfolio
    │
    └── executes Decisions
```

---

# The Knowledge Hierarchy

MRI has five levels of abstraction.

```text
Level 5

Portfolio

↑

Level 4

Decision

↑

Level 3

Knowledge

↑

Level 2

Fact

↑

Level 1

Document
```

Every higher level depends only on the level immediately below it.

---

# Ownership

| Domain Object  | Owner                   |
| -------------- | ----------------------- |
| Company        | Platform                |
| SourceDocument | Research Inbox          |
| Fact           | AKE                     |
| Variable       | Ontology Engine         |
| Knowledge      | KUP + Workspace Updater |
| Decision       | Decision Engine         |
| Portfolio      | Portfolio Engine        |

---

# What Every Component May Read

| Component         | Reads                     |
| ----------------- | ------------------------- |
| Research Inbox    | Company                   |
| AKE               | SourceDocument            |
| Ontology Engine   | Variable, Fact            |
| KUP               | Fact, Variable, Knowledge |
| Workspace Updater | Transactions              |
| Decision Engine   | Knowledge                 |
| Portfolio Engine  | Decision                  |

---

# What Every Component May Write

| Component         | Writes                     |
| ----------------- | -------------------------- |
| Research Inbox    | SourceDocument             |
| AKE               | Fact                       |
| Ontology Engine   | Variable                   |
| KUP               | KnowledgeUpdateTransaction |
| Workspace Updater | Knowledge                  |
| Decision Engine   | Decision                   |
| Portfolio Engine  | Portfolio                  |

---

# Architectural Laws

## Law 1

Documents never become Knowledge directly.

They become Facts first.

---

## Law 2

Facts are immutable.

---

## Law 3

Variables define meaning, not value.

---

## Law 4

Knowledge is always explainable.

Every Knowledge item must trace back to one or more Facts.

---

## Law 5

Decisions never inspect documents.

---

## Law 6

Portfolio never performs AI reasoning.

---

## Law 7

Every service owns exactly one domain object.

---

# The MRI Knowledge Pyramid

```text
                    Portfolio
                        ▲
                        │
                  Investment Decisions
                        ▲
                        │
               Company Knowledge
                        ▲
                        │
                Extracted Facts
                        ▲
                        │
               Source Documents
                        ▲
                        │
                 External Research
```

---

# The One Sentence That Defines MRI

> **MRI transforms external research into structured facts, reconciles those facts into company knowledge, and converts that knowledge into consistent investment decisions.**

---

## My recommendation before writing any more PRDs

At this point, I would stop feature development for a day and assemble these into an **"MRI Architecture Bible"**.

It would contain, in order:

1. **Vision & Principles**
2. **Domain Model & Ubiquitous Language** (this document)
3. **ER Diagram**
4. **Data Dictionary**
5. **Knowledge Lifecycle**
6. **Component Architecture**
7. **API Standards**
8. **Coding Standards**
9. **PRD Template**
10. **Implementation Roadmap**

Then every future PRD would simply say, "Conforms to MRI Architecture Bible v1.0," instead of redefining the architecture. That's how large systems stay coherent over years rather than months.

---

Yes.

And this time I'd start where I should have started this morning: **the data model**, not the services.

The first artifact should not be an AKE diagram. It should be the **persistent knowledge model** that every service uses.

```text
                               MRI KNOWLEDGE DATABASE
                          (Single Source of Truth - PostgreSQL)

                                        ┌──────────────────────┐
                                        │      Company         │
                                        │----------------------│
                                        │ company_id           │
                                        │ ticker              │
                                        │ name                │
                                        └──────────┬──────────┘
                                                   │
                                                   │ 1:N
                                                   ▼
                    ┌─────────────────────────────────────────────────┐
                    │               SourceDocument                    │
                    │-------------------------------------------------│
                    │ document_id                                     │
                    │ company_id (FK)                                 │
                    │ document_type (MOSI, Annual Report...)          │
                    │ markdown                                         │
                    │ uploaded_at                                      │
                    │ version                                          │
                    └──────────────┬───────────────────────────────────┘
                                   │
                                   │ 1:N
                                   ▼
                    ┌─────────────────────────────────────────────────┐
                    │            ExtractedFact                         │
                    │-------------------------------------------------│
                    │ fact_id                                          │
                    │ document_id (FK)                                 │
                    │ company_id (FK)                                  │
                    │ raw_name                                         │
                    │ raw_value                                        │
                    │ confidence                                       │
                    │ page                                              │
                    │ paragraph                                         │
                    │ extractor_version                                 │
                    │ variable_id (nullable FK)                         │
                    └──────────────┬───────────────────────────────────┘
                                   │
                        classified by AKE
                                   │
                                   ▼
                    ┌─────────────────────────────────────────────────┐
                    │             Variable                            │
                    │-------------------------------------------------│
                    │ variable_id                                      │
                    │ canonical_name                                   │
                    │ section                                           │
                    │ datatype                                          │
                    │ status (RESERVE/CANONICAL/...)                   │
                    └──────────────┬───────────────────────────────────┘
                                   │
                     ┌─────────────┴─────────────┐
                     │                           │
                     ▼                           ▼
          VariableAlias                 PromotionHistory
          -----------------            -------------------
          alias_id                     history_id
          variable_id                  variable_id
          alias                        action
                                      reviewer
                                      timestamp
                                      reason

                                   │
                                   │
                                   ▼
                    ┌─────────────────────────────────────────────────┐
                    │          CompanyKnowledge                       │
                    │-------------------------------------------------│
                    │ company_id                                      │
                    │ variable_id                                     │
                    │ current_value                                   │
                    │ confidence                                      │
                    │ source_fact_id                                  │
                    │ updated_at                                      │
                    └─────────────────────────────────────────────────┘
```

Then the services become almost trivial:

```text
Upload PDF
      │
      ▼
SourceDocument
      │
      ▼
AKE
      │
      ├── creates ExtractedFact
      ├── links to Variable
      └── creates new Variable if needed
              │
              ▼
Variable Registry (Ontology)
              │
              ▼
Knowledge Update Processor
              │
              ▼
Knowledge Update Transaction
              │
              ▼
Workspace Updater
              │
              ▼
CompanyKnowledge
```

## I would stop all new coding after this.

Before another line of Python is written, I would produce **three database-first documents**:

1. **ER Diagram** (the one above, expanded properly)
2. **Data Dictionary** (every table, every column, every constraint)
3. **Lifecycle Diagram** (how data moves between tables)

Only after those are approved would I let the AI generate code.

I think this is the missing foundation that should have preceded the AKE PRD. Once this is agreed upon, every subsequent PRD—AKE, KUP, Workspace Updater, Decision Engine—becomes much simpler because they're all operating on a well-defined persistent data model rather than inventing their own view of the world.

---

Agreed. If **Document 1** is the ER Diagram, then **Document 2** should be the **Data Dictionary**. This is the contract that every developer, AI agent, and service must follow.

---

# MRI Knowledge OS

# Document 2: Data Dictionary v1.0

**Status:** Architecture Foundation (P0)

**Purpose**

Define every persistent entity, its attributes, ownership, relationships, constraints, and lifecycle.

This document is the authoritative reference for the MRI Knowledge Database.

---

# 1. Company

### Purpose

Represents a listed company tracked by MRI.

| Field      | Type         | Constraints | Description         |
| ---------- | ------------ | ----------- | ------------------- |
| company_id | UUID         | PK          | Internal identifier |
| ticker     | VARCHAR(20)  | UNIQUE      | NSE/BSE symbol      |
| name       | VARCHAR(255) | NOT NULL    | Company name        |
| sector     | VARCHAR(100) | NULL        | Sector              |
| industry   | VARCHAR(100) | NULL        | Industry            |
| created_at | TIMESTAMP    | NOT NULL    | Creation time       |
| updated_at | TIMESTAMP    | NOT NULL    | Last update         |

---

# 2. SourceDocument

### Purpose

Stores every uploaded research document.

Examples

* MOSI
* Annual Report
* Concall
* Investor Presentation
* Credit Rating Report

| Field             | Type         | Constraints  | Description                        |
| ----------------- | ------------ | ------------ | ---------------------------------- |
| document_id       | UUID         | PK           | Document identifier                |
| company_id        | UUID         | FK → Company | Owner company                      |
| document_type     | ENUM         | NOT NULL     | MOSI, AnnualReport, Concall, etc.  |
| title             | VARCHAR(255) | NOT NULL     | Document title                     |
| source            | VARCHAR(100) | NULL         | Internal, Screener, Exchange, etc. |
| markdown          | TEXT         | NOT NULL     | Parsed markdown                    |
| checksum          | VARCHAR(64)  | UNIQUE       | Prevent duplicate uploads          |
| uploaded_at       | TIMESTAMP    | NOT NULL     | Upload timestamp                   |
| extractor_version | VARCHAR(30)  | NULL         | AKE version used                   |

---

# 3. Variable

### Purpose

Defines the MRI ontology.

This table contains **definitions**, not values.

| Field          | Type         | Constraints | Description                                      |
| -------------- | ------------ | ----------- | ------------------------------------------------ |
| variable_id    | UUID         | PK          | Variable identifier                              |
| canonical_name | VARCHAR(255) | UNIQUE      | e.g. pricing_power                               |
| display_name   | VARCHAR(255) | NOT NULL    | Pricing Power                                    |
| section        | VARCHAR(100) | NOT NULL    | Monitoring, Risks, etc.                          |
| data_type      | ENUM         | NOT NULL    | string, number, boolean, percentage, date        |
| status         | ENUM         | NOT NULL    | RESERVE, CANONICAL, MERGED, REJECTED, DEPRECATED |
| description    | TEXT         | NULL        | Human-readable definition                        |
| created_at     | TIMESTAMP    | NOT NULL    | Created                                          |
| updated_at     | TIMESTAMP    | NOT NULL    | Updated                                          |

---

# 4. VariableAlias

### Purpose

Stores every synonym mapped to a canonical variable.

| Field       | Type         | Constraints   |
| ----------- | ------------ | ------------- |
| alias_id    | UUID         | PK            |
| variable_id | UUID         | FK → Variable |
| alias       | VARCHAR(255) | UNIQUE        |
| created_at  | TIMESTAMP    | NOT NULL      |

Example

| Alias                 | Canonical              |
| --------------------- | ---------------------- |
| Top Customer Exposure | customer_concentration |
| Largest Client Share  | customer_concentration |

---

# 5. ExtractedFact

### Purpose

Stores **every fact extracted** by AKE.

Nothing extracted is discarded.

| Field             | Type         | Constraints                               |
| ----------------- | ------------ | ----------------------------------------- |
| fact_id           | UUID         | PK                                        |
| document_id       | UUID         | FK → SourceDocument                       |
| company_id        | UUID         | FK → Company                              |
| variable_id       | UUID         | FK → Variable (nullable until classified) |
| raw_name          | TEXT         | NOT NULL                                  |
| raw_value         | TEXT         | NOT NULL                                  |
| normalized_value  | JSONB        | NULL                                      |
| confidence        | DECIMAL(4,3) | NOT NULL                                  |
| page_number       | INTEGER      | NULL                                      |
| paragraph_number  | INTEGER      | NULL                                      |
| extractor_version | VARCHAR(30)  | NOT NULL                                  |
| extracted_at      | TIMESTAMP    | NOT NULL                                  |

This table is the permanent evidence layer.

---

# 6. CompanyKnowledge

### Purpose

Represents MRI's **current belief** about a company.

Updated only through KUP.

| Field          | Type         | Constraints        |
| -------------- | ------------ | ------------------ |
| knowledge_id   | UUID         | PK                 |
| company_id     | UUID         | FK → Company       |
| variable_id    | UUID         | FK → Variable      |
| current_value  | JSONB        | NOT NULL           |
| confidence     | DECIMAL(4,3) | NOT NULL           |
| source_fact_id | UUID         | FK → ExtractedFact |
| effective_date | DATE         | NULL               |
| updated_at     | TIMESTAMP    | NOT NULL           |

Unique Constraint:

```text
(company_id, variable_id)
```

Only one current belief exists per variable per company.

---

# 7. KnowledgeHistory

### Purpose

Immutable audit trail of every accepted change.

| Field          | Type         | Constraints |
| -------------- | ------------ | ----------- |
| history_id     | UUID         | PK          |
| company_id     | UUID         | FK          |
| variable_id    | UUID         | FK          |
| old_value      | JSONB        | NULL        |
| new_value      | JSONB        | NOT NULL    |
| source_fact_id | UUID         | FK          |
| changed_by     | VARCHAR(100) | System/User |
| changed_at     | TIMESTAMP    | NOT NULL    |

Never updated.

Never deleted.

Append only.

---

# 8. PromotionHistory

### Purpose

Records ontology evolution.

| Field           | Type         |
| --------------- | ------------ |
| history_id      | UUID         |
| variable_id     | UUID         |
| previous_status | ENUM         |
| new_status      | ENUM         |
| reviewer        | VARCHAR(100) |
| reason          | TEXT         |
| timestamp       | TIMESTAMP    |

---

# 9. KnowledgeUpdateTransaction

### Purpose

Represents a single reconciliation run by KUP.

| Field              | Type      |
| ------------------ | --------- |
| transaction_id     | UUID      |
| company_id         | UUID      |
| source_document_id | UUID      |
| status             | ENUM      |
| started_at         | TIMESTAMP |
| completed_at       | TIMESTAMP |

---

# 10. KnowledgeUpdateOperation

### Purpose

Individual operations within a transaction.

| Field          | Type                                         |
| -------------- | -------------------------------------------- |
| operation_id   | UUID                                         |
| transaction_id | UUID                                         |
| variable_id    | UUID                                         |
| action         | ENUM (ADD, UPDATE, IGNORE, CONFLICT, REMOVE) |
| old_value      | JSONB                                        |
| new_value      | JSONB                                        |
| confidence     | DECIMAL(4,3)                                 |

---

# Ownership Matrix

| Table                      | Owner             |
| -------------------------- | ----------------- |
| Company                    | Platform          |
| SourceDocument             | Research Inbox    |
| Variable                   | Ontology Engine   |
| VariableAlias              | Ontology Engine   |
| ExtractedFact              | AKE               |
| CompanyKnowledge           | Workspace Updater |
| KnowledgeHistory           | Workspace Updater |
| PromotionHistory           | Ontology Engine   |
| KnowledgeUpdateTransaction | KUP               |
| KnowledgeUpdateOperation   | KUP               |

---

# Design Principles

1. **Single Source of Truth** – Every fact is stored exactly once and referenced thereafter.
2. **Separation of Concerns** – Definitions (Variable), evidence (ExtractedFact), current belief (CompanyKnowledge), and history (KnowledgeHistory) are separate entities.
3. **Append-Only Audit** – Historical records are never modified or deleted.
4. **Traceability** – Every value in `CompanyKnowledge` can be traced back to the originating `ExtractedFact` and `SourceDocument`.
5. **Ontology Evolution** – Variables evolve independently of extracted facts, allowing the ontology to mature without losing historical evidence.

This data dictionary becomes the contract for every future PRD. AKE, KUP, the Workspace Updater, the Decision Engine, and any analytics or screening components should interact with these entities rather than inventing new storage structures.

---

Perfect. Now we get to the document that ties everything together.

Documents 1 and 2 answer:

* **What data exists?**
* **Where is it stored?**

Document 3 answers:

* **How does data move?**
* **Who owns each step?**
* **What can modify what?**

This is the operational blueprint.

---

# MRI Knowledge OS

# Document 3: Data Lifecycle & Knowledge Flow v1.0

**Status:** Architecture Foundation (P0)

**Purpose**

Define the lifecycle of knowledge from ingestion to decision-making, including ownership, state transitions, transaction boundaries, and invariants.

---

# 1. Guiding Principle

Knowledge moves through MRI in **four distinct stages**.

```text
RAW DOCUMENT
      │
      ▼
EXTRACTED FACT
      │
      ▼
CANONICAL KNOWLEDGE
      │
      ▼
DECISION INTELLIGENCE
```

Each stage has exactly one owner.

---

# 2. Complete Knowledge Flow

```text
                ┌────────────────────────┐
                │  Upload Research PDF   │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │     SourceDocument     │
                │ (Markdown Repository)  │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │ Adaptive Knowledge     │
                │ Extraction Engine      │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │     ExtractedFact      │
                └────────────┬───────────┘
                             │
                    Classify / Match
                             │
                             ▼
                ┌────────────────────────┐
                │ Variable Ontology      │
                │ (Registry)             │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │ Knowledge Update       │
                │ Processor              │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │ Knowledge Transaction  │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │ Workspace Updater      │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │ Company Knowledge      │
                └────────────┬───────────┘
                             │
                             ▼
                Decision Engine
```

---

# 3. Ownership Matrix

| Stage                 | Owner             | Can Modify              |
| --------------------- | ----------------- | ----------------------- |
| SourceDocument        | Research Inbox    | SourceDocument          |
| ExtractedFact         | AKE               | ExtractedFact           |
| Variable              | Ontology Engine   | Variable, Alias         |
| Knowledge Transaction | KUP               | Transaction tables only |
| CompanyKnowledge      | Workspace Updater | CompanyKnowledge        |
| Decision Engine       | MRI Core          | Nothing upstream        |

No component may write outside its ownership boundary.

---

# 4. State Machine

## SourceDocument

```text
UPLOADED
      │
      ▼
PARSED
      │
      ▼
READY_FOR_EXTRACTION
      │
      ▼
PROCESSED
```

---

## ExtractedFact

```text
CREATED
      │
      ▼
UNCLASSIFIED
      │
      ├─────────────┐
      ▼             ▼
MATCHED        NEW VARIABLE
      │             │
      ▼             ▼
LINKED      RESERVE VARIABLE
```

Facts are immutable once created.

---

## Variable

```text
DISCOVERED
      │
      ▼
RESERVE
      │
 ┌────┴────┐
 ▼         ▼
CANONICAL  REJECTED
     │
     ▼
DEPRECATED
```

---

## CompanyKnowledge

```text
NEW
 │
 ▼
ACTIVE
 │
 ▼
UPDATED
 │
 ▼
SUPERSEDED
```

No row is physically deleted.

---

# 5. Transaction Boundaries

### Transaction 1 — Document Ingestion

```
Upload
↓

Create SourceDocument

↓

Commit
```

---

### Transaction 2 — Extraction

```
Read SourceDocument

↓

Create ExtractedFact rows

↓

Commit
```

No CompanyKnowledge changes occur here.

---

### Transaction 3 — Ontology

```
Review Variable

↓

Approve / Reject / Merge

↓

Commit
```

Only ontology changes.

---

### Transaction 4 — Knowledge Update

```
Read CompanyKnowledge

↓

Read ExtractedFact

↓

Generate UpdateTransaction

↓

Commit
```

No workspace writes yet.

---

### Transaction 5 — Workspace Update

```
Read Transaction

↓

Update CompanyKnowledge

↓

Append KnowledgeHistory

↓

Commit
```

Atomic.

---

# 6. System Invariants

These must always hold.

### Invariant 1

Every CompanyKnowledge row references exactly one ExtractedFact.

---

### Invariant 2

Every ExtractedFact references exactly one SourceDocument.

---

### Invariant 3

Every canonical Variable has exactly one definition.

---

### Invariant 4

History is append-only.

---

### Invariant 5

AKE never updates CompanyKnowledge.

---

### Invariant 6

KUP never parses Markdown.

---

### Invariant 7

WorkspaceUpdater never performs AI reasoning.

---

# 7. Failure Recovery

If AKE crashes:

```
SourceDocument

READY_FOR_EXTRACTION
```

Retry safely.

---

If KUP crashes:

```
KnowledgeTransaction

FAILED
```

Retry.

---

If WorkspaceUpdater crashes:

Rollback transaction.

No partial updates.

---

# 8. Provenance Chain

Every decision in MRI must be traceable.

```
Decision
    │
    ▼
CompanyKnowledge
    │
    ▼
ExtractedFact
    │
    ▼
SourceDocument
    │
    ▼
Original PDF
```

This is the "explainability chain."

---

# 9. Component Responsibilities

| Component         | Responsibility               | Never Does       |
| ----------------- | ---------------------------- | ---------------- |
| Research Inbox    | Ingest documents             | AI extraction    |
| AKE               | Extract facts                | Update workspace |
| Ontology Engine   | Define variables             | Parse documents  |
| KUP               | Reconcile facts              | Run LLMs         |
| Workspace Updater | Persist accepted knowledge   | Infer meaning    |
| Decision Engine   | Produce investment decisions | Modify knowledge |

---

# 10. Guiding Architectural Rules

1. **Documents are immutable.**
2. **Facts are immutable.**
3. **Ontology evolves under controlled review.**
4. **Company knowledge is the current accepted view.**
5. **History is never rewritten.**
6. **Every downstream value must be explainable back to an uploaded document.**
7. **Each service has one responsibility and one persistence boundary.**

---

## One addition I'd make before freezing these three documents

I'd add a **Document 0** that sits above all of them:

> **MRI Knowledge Domain Model**

It would define, in plain English, the core concepts:

* Company
* SourceDocument
* Fact
* Variable
* Knowledge
* Decision

Every PRD would then use those exact terms consistently. That prevents terminology drift (e.g., "fact" vs. "variable" vs. "candidate") as the system grows.

With these four documents:

1. **ER Diagram**
2. **Data Dictionary**
3. **Data Lifecycle & Knowledge Flow**
4. **Knowledge Domain Model**

you have a stable architectural foundation. Every future PRD should reference them rather than redefining core concepts, which will keep the AI-generated implementation aligned as MRI evolves.

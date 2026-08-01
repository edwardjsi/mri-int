# Execution Statement: MOSI Compiler v1.0

## Instructions to Engineering Team
> **Proceed with implementation. The architecture is frozen for Version 1. Deliver a working vertical slice before proposing architectural improvements.**

### 1. Build, don't redesign
> The architecture for MOSI Compiler V1 is frozen. If you discover a better design while implementing, record it, but do not stop Milestone 1 to redesign the system. The objective is to prove the end-to-end pipeline.

### 2. Optimize for working software
The success criterion is not beautiful code. The success criterion is:
`Golden MOSI` → `Compile` → `4 JSON artifacts` → `Import` → `Company Knowledge page`
If this works, V1 is a success.

### 3. Escalate instead of assuming
If any part of the specification is ambiguous:
* don't invent architecture
* don't silently change the contract
* raise the question
The compiler contract is more important than implementation elegance.

---

## 1. Objective
**Prove that a single MOSI report can be transformed into a complete, auditable, versioned Company Knowledge Base.** 
The goal is not just writing code; it is proving the extraction pipeline works reliably and immutably.

## 2. Compilation Status Lifecycle
Every company will possess exactly one compilation status state:
`NOT_STARTED` → `COMPILING` → `COMPILED` → `VALIDATED` → `FAILED`

## 3. Explicit Architectural Boundary
> **The compiler must not call any CAI Decision, Rule, Evidence, Inference, Policy, or Resolution engine. Its sole responsibility ends with producing structured knowledge artifacts.**

## 4. Explicit Non-Goals (V1)
The MOSI Compiler does NOT:
- calculate indicators
- create observations
- create evidence
- create inferences
- create hypotheses
- calculate scores
- generate recommendations
- evaluate portfolio policy
- compare quarters
- merge historical knowledge

Those responsibilities belong to downstream engines.

## 5. Compiler Contract
**Input:**
- One MOSI Report

**Output:**
- One immutable Company Knowledge Version

**Properties:**
- Deterministic
- Repeatable
- Auditable
- Versioned
- Explainable

## 6. Deliverables
1. `company_facts.json`
2. `company_knowledge.json`
3. `extraction_report.json`
4. `knowledge_manifest.json`
5. **Company Knowledge Debugging UI Page**: A simple page capable of displaying Granules' Business, Plants, Products, Management, Financials, Risks, Facts, Evidence, and the Compiler Report to visually inspect output.

## 7. Implementation Milestones

### Milestone 1: The Pipeline Proof (Mock to UI)
Build the entire pipeline using manually prepared JSON output from one "Golden MOSI" report.
- Establish the **Golden MOSI**:
  - **Company**: Granules India
  - **Purpose**: Permanent regression dataset.
  - **Rule**: This report SHALL NEVER change. Every future compiler version must successfully compile this report. If a new compiler cannot reproduce the Golden MOSI outputs, the build fails.
- Process the mock data through the compiler script to produce the exactly formatted 4 JSON files.
- Render the JSON onto the Company Knowledge UI Page.

### Milestone 2: AI Extraction Integration
Only after Milestone 1 works flawlessly:
- Replace the mock JSON with true deterministic parsing and LLM extraction.
- Apply rigorous `verify_evidence` string grounding.

## 8. Acceptance Tests (Definition of Done for V1)
- [ ] Four artifacts created.
- [ ] Every extracted field must either be traceable to explicit source evidence, or be null.
- [ ] All evidence links resolve.
- [ ] Every fact has an ID.
- [ ] Every entity has an ID.
- [ ] Every fact has temporal context.
- [ ] Every fact has provenance.
- [ ] Compiler is deterministic (running twice produces identical output).
- [ ] Importing the same Golden MOSI twice must not create duplicate knowledge.
- [ ] Company Knowledge page renders without errors against the Golden MOSI.

---

# Architect's Notes

> **If implementing any of these recommendations would materially delay Milestone 1 (proving the Golden MOSI end-to-end), defer them. Shipping a working vertical slice is more important than perfect architecture.**

### 1. Compiler must be stateless (Recommended)
The MOSI Compiler should not own the Knowledge Repository.
`MOSI Report` → `MOSI Compiler` → `4 JSON Artifacts` → `Knowledge Importer` → `Knowledge Repository`
The compiler's responsibility ends once it produces the artifacts. Importing, validation, versioning, and persistence belong to a separate component.

### 2. Add an Import milestone
After the compiler successfully generates the artifacts:
* Validate all four artifacts.
* Import them into the repository.
* Reject invalid imports.
* Version successful imports.
* Record compilation history.

### 3. Treat "Four Artifacts" as Version 1
Instead of making four artifacts a permanent rule, define them as the required outputs for Version 1. This keeps the design extensible for future additions without changing the compiler contract.

### 4. Suggested Implementation Roadmap
1. MOSI Compiler
2. Knowledge Importer
3. Company Knowledge UI
4. Quarterly Results Compiler
5. Quarterly Delta Merger
6. Observation Engine
7. Rule & Evidence Engine
8. Decision Engine

The Decision Engine should be built only after the Knowledge Base has proven itself.

# Execution Statement: MOSI Compiler v1.0

## 1. Objective
**Prove that a single MOSI report can be transformed into a complete, auditable, versioned Company Knowledge Base.** 
The goal is not just writing code; it is proving the extraction pipeline works reliably and immutably.

## 2. Compilation Status Lifecycle
Every company will possess exactly one compilation status state:
`NOT_STARTED` → `COMPILING` → `COMPILED` → `VALIDATED` → `FAILED`

## 3. Explicit Architectural Boundary
> **The compiler must not call any CAI Decision, Rule, Evidence, Inference, Policy, or Resolution engine. Its sole responsibility ends with producing structured knowledge artifacts.**

## 4. Deliverables
1. `company_facts.json`
2. `company_knowledge.json`
3. `extraction_report.json`
4. `knowledge_manifest.json`
5. **Company Knowledge Debugging UI Page**: A simple page capable of displaying Granules' Business, Plants, Products, Management, Financials, Risks, Facts, Evidence, and the Compiler Report to visually inspect output.

## 5. Implementation Milestones

### Milestone 1: The Pipeline Proof (Mock to UI)
Build the entire pipeline using manually prepared JSON output from one "Golden MOSI" report.
- Establish the **Golden MOSI** (Granules MOSI report frozen in time as a permanent regression test).
- Process the mock data through the compiler script to produce the exactly formatted 4 JSON files.
- Render the JSON onto the Company Knowledge UI Page.

### Milestone 2: AI Extraction Integration
Only after Milestone 1 works flawlessly:
- Replace the mock JSON with true deterministic parsing and LLM extraction.
- Apply rigorous `verify_evidence` string grounding.

## 6. Acceptance Tests (Definition of Done for V1)
- [ ] Four artifacts created.
- [ ] Zero hallucinated fields.
- [ ] All evidence links resolve.
- [ ] Every fact has an ID.
- [ ] Every entity has an ID.
- [ ] Every fact has temporal context.
- [ ] Every fact has provenance.
- [ ] Compiler is deterministic (running twice produces identical output).
- [ ] Company Knowledge page renders without errors against the Golden MOSI.

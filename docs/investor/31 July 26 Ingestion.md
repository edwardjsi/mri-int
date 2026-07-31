Absolutely — those three changes are the right ones, and I agree they are **mandatory** before calling it v1.1 Final. They make the workflow safer, clearer, and much more aligned with MRI’s “knowledge update” model.

## What I changed
I incorporated:
- A **single canonical pipeline** with no “routing” as a product concept.
- A new **Preview Ready** state before knowledge mutation.
- A **Workspace Diff** preview showing the exact proposed changes.
- The button label **Update Company Knowledge** instead of Upload or Process.

## Final Engineering PRD
Here is the revised version.

# Engineering PRD: Research Inbox V1.1 Final

**Version:** v1.1 Final  
**Priority:** P0  
**Owner:** Engineering  
**Depends on:** MRI System Architecture v1.0, Company Intelligence Workspace, MOSI pipeline, company identity model  
**Frontend Contract Version:** v1.1  
**Backend Contract Version:** v1.1

## 1. Objective
Build a Research Inbox that accepts research documents, extracts readable text using Microsoft MarkItDown, stages the extracted content for human verification, and applies a knowledge update to the canonical Company Workspace.

The product does not end when text is extracted. It ends when the user sees the proposed workspace changes and commits the update.

## 2. North Star
Every UI and backend decision must reduce the time from document upload to safe, visible company understanding change.

## 3. Canonical pipeline
There is one canonical pipeline:

Research Inbox  
↓  
KnowledgeIngestionService  
↓  
SourceDocument  
↓  
KnowledgeUpdateProcessor  
↓  
KnowledgeUpdateTransaction  
↓  
WorkspaceUpdater  
↓  
Company Workspace

There is no routing decision in the product model. Every supported source ultimately becomes markdown-like structured text that feeds the same knowledge update pipeline.

## 4. Scope

### In scope
- Inbox list view.
- Document intake.
- Duplicate detection.
- Company auto-detection.
- MarkItDown parsing in the backend image.
- Extracted text preview.
- Workspace diff preview.
- Preview Ready state.
- Knowledge update commit flow.
- Open Workspace action.
- Research history on company workspace.
- Error visibility.
- Retry / reprocess flow.
- Audit trail and logging.

### Out of scope
- Charts.
- AI summaries.
- Decision engine logic.
- Portfolio OS mutation.
- Manual text editing of extracted content.
- Cross-company analytics.
- News feeds.
- Technical analysis.
- Human review workflow outside the Preview Ready step.
- Client-side business logic.

## 5. Architectural rules

### 5.1 Bounded-context alignment
#### Research Inbox owns
- Intake.
- File registration.
- Duplicate detection.
- Parse execution.
- Company inference.
- Preview preparation.
- Knowledge update initiation.
- Status transitions.
- Audit and logging.

#### Company Intelligence Workspace owns
- Canonical company knowledge.
- Workspace refresh.
- Research history display.
- What changed presentation.

#### Downstream bounded contexts own
- MOSI interpretation.
- Decision logic.
- Portfolio effects.

### 5.2 Frontend must never
- Infer company update meaning.
- Calculate knowledge deltas.
- Reclassify statuses.
- Create company knowledge directly.
- Mutate downstream objects.
- Hide raw file evidence.
- Commit knowledge updates without preview.

## 6. Technical choice: MarkItDown
MarkItDown should be installed in the backend application image, not isolated as a separate service.

### Rationale
- It is a parsing library, not a network service.
- Simpler deployment.
- Lower operational overhead.
- Easier local development.
- Sufficient for V1 scale.

### Backend stack placement
Backend  
→ FastAPI  
→ KnowledgeIngestionService  
→ MarkItDown  
→ KnowledgeUpdateProcessor  
→ WorkspaceUpdater

## 7. UX flow

### Primary flow
1. User uploads a file.
2. System stores raw file and creates inbox record.
3. System auto-detects target company.
4. System checks for duplicates.
5. System parses the document with MarkItDown.
6. System shows Preview Ready.
7. User reviews original PDF, extracted markdown, and workspace diff.
8. User clicks Update Company Knowledge.
9. System runs knowledge update processing.
10. System updates the Company Workspace.
11. Success screen shows what changed.
12. User can click Open Workspace.

### Duplicate flow
- If the document was already processed, show already processed state.
- Offer reprocess if allowed.
- Show existing workspace version and prior upload time.

### Low-confidence company detection flow
- Try filename inference.
- Try markdown metadata.
- Try LLM extraction.
- Ask user only if confidence remains low.

## 8. Frontend screens

### 8.1 Inbox List
#### Purpose
Show all research documents entering or moving through the pipeline.

#### Must display
- Document name.
- Company.
- Status.
- Received time.
- Last processed time.
- Workspace version if processed.
- Duplicate indicator if applicable.

### 8.2 Upload Screen
#### Purpose
Let the user upload a research document.

#### Must display
- File picker.
- Drop zone.
- Optional company suggestion if confidence is high.
- Update Company Knowledge action.

### 8.3 Document Detail
#### Purpose
Show document state, previews, and processing details.

#### Must display
- Original PDF tab.
- Extracted Markdown tab.
- Workspace Diff tab.
- Processing status.
- Parsed output summary.
- Duplicate status.
- Retry / reprocess action if supported.

### 8.4 Preview Ready
#### Purpose
Let the user inspect parsed content before any knowledge mutation occurs.

#### Must display
- Original PDF preview.
- Extracted Markdown preview.
- Workspace Diff preview.
- Company detected.
- Workspace version that will be created or updated.
- Update Company Knowledge button.

#### UX rule
The system must not mutate company knowledge until the user approves the preview.

### 8.5 Knowledge Updated Success Screen
#### Purpose
Show the user that the company workspace has changed.

#### Must display
- Company name.
- Workspace updated confirmation.
- Thesis updated.
- Business quality updated.
- Catalysts added / changed.
- Risks added / changed.
- Monitoring items added / changed.
- Previous thesis archived.
- Workspace version.
- Open Workspace button.

#### UX rule
This is the magic moment. The user should immediately see that their research changed the company’s understanding.

## 9. Workspace Diff
The Workspace Diff must show what is about to change before the user commits the update.

### Must display
- Current Thesis.
- New Thesis.
- New Catalyst additions.
- New Risk additions.
- Monitoring additions.
- Updated sections.
- Archived prior statement if applicable.

### Example
- Current Thesis: Stable growth.
- New Thesis: Growth acceleration confirmed.
- New Catalyst: Capacity expansion.
- New Risk: USFDA inspection.
- Monitoring: EBITDA margin, capacity utilization.

### UX rule
The user is reviewing knowledge, not documents.

## 10. Research history
The company workspace must display a research history section.

### Each item must show
- File name.
- Processed status.
- Uploaded time.
- Processed time.
- Workspace version.
- Open document action.

### UX rule
Documents must not disappear into the pipeline.

## 11. State transitions

### Document lifecycle
Received  
→ Company Detected  
→ Duplicate Check  
→ Parsing  
→ Preview Ready  
→ Knowledge Updating  
→ Workspace Updated  
→ Success Shown  
→ Open Workspace

### Failure path
Received / Parsing / Preview Ready / Knowledge Updating  
→ Failed  
→ Retryable if supported

### Duplicate path
Received  
→ Duplicate Detected  
→ Already Processed / Reprocess

### Transition ownership
- Backend validates transitions.
- Frontend only renders them.

## 12. Company detection logic

### Priority order
1. Filename inference.
2. Markdown metadata extraction.
3. LLM extraction.
4. User confirmation if confidence is low.

### Rules
- Use backend-owned confidence.
- The UI must show the selected company and confidence if provided.
- If multiple candidates exist, ask the user to choose.
- If confidence is low, do not auto-commit silently.

## 13. Duplicate detection
The system must detect when a file has already been processed.

### Duplicate state must show
- Already processed.
- Prior workspace version.
- Prior upload time.
- Reprocess option if allowed.

### UX rule
Accidental duplicate updates must be visible before processing proceeds.

## 14. API contracts

### 14.1 Upload document
`POST /api/research-inbox/items`

Request:
```json
{
  "filename": "neuland_q1.pdf",
  "contentType": "application/pdf"
}
```

Response:
```json
{
  "inboxId": "rin_001",
  "status": "Received",
  "receivedAt": "2026-07-31T10:00:00Z"
}
```

### 14.2 Detect company
`POST /api/research-inbox/items/{inboxId}/detect-company`

### 14.3 Check duplicate
`GET /api/research-inbox/items/{inboxId}/duplicate-check`

### 14.4 Parse document
`POST /api/research-inbox/items/{inboxId}/parse`

### 14.5 Preview ready
`GET /api/research-inbox/items/{inboxId}/preview`

### 14.6 Commit knowledge update
`POST /api/research-inbox/items/{inboxId}/update-workspace`

Response:
```json
{
  "inboxId": "rin_001",
  "status": "Workspace Updated",
  "companyId": "cmp_001",
  "workspaceVersion": 44,
  "updatedSections": [
    "Current Understanding",
    "Current Risks",
    "Monitoring"
  ]
}
```

### 14.7 Get inbox item
`GET /api/research-inbox/items/{inboxId}`

### 14.8 List inbox items
`GET /api/research-inbox/items?companyId=cmp_001`

## 15. Logging and audit
Log:
- upload received.
- company detection result.
- duplicate detection result.
- parse start and end.
- preview ready.
- knowledge update start and end.
- success screen shown.
- open workspace action.
- retry / reprocess action.

Audit record must preserve:
- raw document identity.
- company identity.
- parse output identity.
- workspace version produced.
- duplicate detection outcome.
- user approval before commit.

## 16. Testing strategy

### Unit
- company detection priority.
- duplicate detection.
- status transitions.
- preview payload generation.
- update-workspace payload generation.

### Integration
- upload → detect → parse → preview → update → success flow.
- duplicate upload flow.
- low-confidence company selection flow.
- original/extracted/diff preview flow.

### Contract
- inbox APIs.
- preview payload.
- workspace update payload.
- parsed markdown payload.

### End-to-end
- user uploads PDF.
- system parses and shows Preview Ready.
- user reviews Workspace Diff.
- user clicks Update Company Knowledge.
- system updates company workspace.
- user sees success screen.
- user opens workspace.
- workspace reflects the update.
- duplicate upload shows prior processing.

## 17. Deployment considerations
- Backend image includes MarkItDown.
- Workspace updater and inbox release together unless contract version changes.
- Feature flags may gate auto-detection and LLM fallback.
- Reprocessing must be safe across deploys.
- Schema versioning must be explicit.

## 18. Future extensibility
The design must allow future support for:
- OCR.
- Email ingestion.
- Folder sync.
- Multiple parser backends.
- Human correction flow.
- Batch uploads.
- Cross-company ingestion metrics.
- Confidence scoring improvements.
- Workflow notifications.

## 19. Acceptance criteria
The feature is complete when:
1. A user can upload a PDF and see the Company Workspace updated without any developer intervention.
2. The system auto-detects company or asks only when confidence is low.
3. Duplicate uploads are detected before creating duplicate workspace updates.
4. The user can preview both original PDF and extracted markdown.
5. The user can review a Workspace Diff before committing knowledge changes.
6. The user can open the updated workspace immediately from the success screen.
7. Research history appears on the company workspace.
8. MarkItDown runs inside the backend image.
9. The workflow ends with visible changed knowledge, not just parsing.
10. All state transitions are logged.
11. All integration, contract, and E2E tests pass.

## 20. Final implementation rule
If a field, label, or behavior is not explicitly specified in this document, the team must treat it as out of scope until approved.

Yes, I would. 

In fact, I think it's reached the point where **further discussion has diminishing returns**. The remaining improvements are things you'll discover by building and using it, not by adding more pages to the PRD.

That said, I'd give the AI team **three implementation instructions** alongside the PRD.

---

## 1. Build a vertical slice first

Don't build every endpoint and screen before testing.

Ask them to prove this exact flow works:

```text
Upload PDF

↓

MarkItDown

↓

Preview Ready

↓

Workspace Diff

↓

Update Company Knowledge

↓

Company Workspace Updated

↓

Open Workspace
```

With **one real MOSI report** (for example, Neuland Labs).

Once that works end-to-end, then expand the inbox features.

---

## 2. Don't over-engineer v1

Tell them explicitly:

* No message queues.
* No microservices.
* No separate parser container.
* No asynchronous orchestration unless genuinely needed.
* Keep MarkItDown inside the backend application.
* Keep the pipeline synchronous for v1 if processing times are acceptable.

You can always evolve the architecture later if scale demands it.

---

## 3. Define the "Definition of Done"

I would tell the team not to consider the feature complete until this scenario works:

> I drag a real PDF into MRI, inspect the extracted Markdown, review the proposed workspace changes, click **Update Company Knowledge**, open the Company Workspace, and immediately see the updated thesis, risks, catalysts, monitoring items, timeline, and workspace version—without any developer intervention.

If that experience works smoothly, the feature is done.

---

## One thing I would add after implementation

Before moving on to MP3s or earnings calls, spend a week using this workflow yourself.

Try processing 20–30 real documents. You'll quickly notice things like:

* Where auto-detection fails.
* Whether the Workspace Diff is clear enough.
* Whether the success screen shows the right information.
* Whether MarkItDown struggles with particular PDFs.

Those observations are much more valuable than trying to anticipate every edge case in the PRD.



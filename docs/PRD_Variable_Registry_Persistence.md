# Engineering PRD: Persistent Variable Registry

**Version:** 1.0  
**Priority:** P0  
**Owner:** Engineering  
**Depends on:** MRI System Architecture v1.0, Adaptive Knowledge Extraction Engine (AKE) v1.0  

---

## 1. Goals and Non-Goals

### Goals
- Replace the in-memory `VARIABLE_REGISTRY` mock with a robust PostgreSQL schema.
- Persist extracted variables so they survive server restarts and can be consumed safely by the Knowledge Update Processor (KUP).
- Support state transitions for variables (`RESERVE`, `CANONICAL`, `MERGED`, `REJECTED`).
- Provide atomic transaction boundaries for variable promotion and alias merging.
- Ensure strict database constraints to prevent duplicate canonical variables per company section.

### Non-Goals
- Modifying the Knowledge Update Processor (KUP). This PRD solely handles the persistence layer for AKE.
- Building new UI components (The AkeDashboard is already built and will just consume the updated API).
- Implementing the LLM extraction logic (already handled by AKE).

---

## 2. Domain Model

The aggregate root of this context is the `Variable`.

**Properties:**
- `id`: UUID (Primary Key)
- `canonical_name`: The snake_case normalized name.
- `section`: The logical area of the domain it belongs to (e.g., 'Monitoring', 'Risks'). Note: The Registry does not map this to a specific Workspace field; that is KUP's responsibility.
- `data_type`: Type of data (e.g., 'percentage', 'string', 'boolean').
- `status`: Enum representing the current state of the variable (`DISCOVERED`, `RESERVE`, `CANONICAL`, `MERGED`, `DEPRECATED`).
- `created_at`: Timestamp.

The `Variable` acts as the single source of truth for identity, while occurrences, aliases, and lifecycle history are tracked in relation to it.

---

## 3. Database Schema

A new schema will be added to the MRI PostgreSQL database. It normalizes identity, occurrence, aliases, and lifecycle.

### Table: `ake_variable`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique identifier for the variable |
| `canonical_name` | VARCHAR(255) | NOT NULL | Normalized schema name |
| `section` | VARCHAR(100) | NOT NULL | Logical group (e.g., 'Risks') |
| `data_type` | VARCHAR(50) | NOT NULL | Expected value type |
| `status` | VARCHAR(50) | NOT NULL | Current state (see State Machine) |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Timestamp of creation |

### Table: `ake_variable_occurrence`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `variable_id` | UUID | FK -> `ake_variable(id)` | Which variable this represents |
| `company_id` | VARCHAR(50) | NOT NULL | Which company this applies to |
| `source_document_id`| UUID | NOT NULL | Provenance link to the source document |
| `raw_name` | VARCHAR(255) | NOT NULL | The original extracted name |
| `value` | TEXT | NOT NULL | The extracted value |
| `confidence` | FLOAT | NOT NULL | Extraction confidence score |
| `extractor_version`| VARCHAR(50) | NOT NULL | Which AKE version extracted this |
| `created_at` | TIMESTAMP | DEFAULT NOW() | When this occurrence was found |

### Table: `ake_variable_alias`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `variable_id` | UUID | FK -> `ake_variable(id)` | Which canonical variable this maps to |
| `alias` | VARCHAR(255) | NOT NULL | The merged/synonymous raw name |
| `created_at` | TIMESTAMP | DEFAULT NOW() | When it was merged |

### Table: `ake_promotion_history`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique identifier |
| `variable_id` | UUID | FK -> `ake_variable(id)` | Which variable was affected |
| `action` | VARCHAR(50) | NOT NULL | The lifecycle event (e.g., PROMOTED, MERGED, REJECTED) |
| `user_id` | VARCHAR(100)| NOT NULL | Who performed the action |
| `reason` | TEXT | NULL | Review comment or justification (Future proofing) |
| `timestamp` | TIMESTAMP | DEFAULT NOW() | When the event occurred |

### Indexes & Constraints
- **Unique Index:** `UNIQUE(canonical_name, section)` WHERE `status = 'CANONICAL'` to ensure we never promote two variables with the same canonical name to the same section.
- **Index:** on `ake_variable(status)` to accelerate querying the Human Review Queue (`RESERVE`).
- **Index:** on `ake_variable_occurrence(variable_id, company_id)`.

---

## 4. State Machine

The `status` column governs the lifecycle of a `Variable`.

- **DISCOVERED**: Transient state immediately post-extraction.
- **RESERVE**: The variable has accumulated occurrences and is awaiting human review.
- **CANONICAL**: Approved and promoted. Ready to be mapped and consumed by the KUP.
- **MERGED**: The variable was semantically identical to another and has been merged.
- **DEPRECATED**: The variable is no longer useful or extracted.

**Valid Transitions:**
- `RESERVE` -> `CANONICAL` (Approve)
- `RESERVE` -> `DEPRECATED` (Reject)
- `RESERVE` -> `MERGED` (Merge Alias)

All transitions must insert a record into `ake_promotion_history`.

---

## 5. APIs

The existing `api/extractor.py` router will be updated to interact with the database instead of the in-memory dict.

- `GET /api/extractor/variables/reserve`: Returns all variables where `status='RESERVE'`.
- `GET /api/extractor/variables/canonical`: Returns all variables where `status='CANONICAL'`.
- `POST /api/extractor/variables/{id}/promote`: Updates status to `CANONICAL`.
- `POST /api/extractor/variables/{id}/reject`: Updates status to `REJECTED`.
- `POST /api/extractor/variables/{id}/merge`: Updates status to `MERGED`, appends `raw_name` to the target variable's `aliases` JSONB array.

---

## 6. Repository / Service Architecture

To keep the API layer clean, we will implement the Repository Pattern.

### `VariableRegistryRepository`
- `get_by_status(status: str) -> List[Variable]`
- `get_by_id(var_id: UUID) -> Variable`
- `get_occurrences(var_id: UUID) -> List[VariableOccurrence]`
- `save_occurrence(occurrence: VariableOccurrence)`
- `save(variable: Variable)`
- `merge(source_id: UUID, target_canonical_name: str, reason: str)`
- `promote(var_id: UUID, reason: str)`

This abstracts away the raw SQL joins (to fetch occurrences and aliases when loading a `Variable`) and allows us to easily mock the database in unit tests.

---

## 7. Transaction Boundaries

- **Promotion**: Promoting a variable requires updating the `status` and simultaneously inserting a record into `ake_promotion_history`. This is an atomic transaction.
- **Merging**: Merging requires a multi-table transaction:
  1. Retrieve Target Variable.
  2. Retrieve Source Variable.
  3. Insert a new row in `ake_variable_alias` linking the Source's `raw_name` to the Target's `id`.
  4. Change Source's `status` to `MERGED`.
  5. Insert a record into `ake_promotion_history`.
  6. Commit all changes simultaneously.

---

## 8. Migration Plan

1. Execute the SQL schema script to create `ake_variable_registry`.
2. Delete the `VARIABLE_REGISTRY` mock dictionary from `api/extractor.py`.
3. Wire the `api/extractor.py` endpoints to instantiate and call the `VariableRegistryRepository`.
4. (Optional) Run a one-time seed script to insert the 3 mock variables currently hardcoded into the new DB so the UI continues to function for demonstrations.

---

## 9. Error Handling and Concurrency

- **Unique Constraint Violations**: If a user attempts to promote a variable whose `canonical_name` already exists as `CANONICAL` in that section, the DB will throw a unique constraint error. The API must catch this and return a `409 Conflict` prompting the user to Merge instead.
- **Optimistic Locking**: For V1, the chance of concurrent human reviewers mutating the same variable is exceptionally low. Standard PostgreSQL row-level locks during UPDATEs will suffice.

---

## 10. Test Strategy

- **Unit Tests**: Test the Repository logic (specifically the Merge transaction logic) using a mocked database connection.
- **Integration Tests**: Hit the API endpoints using the FastApi TestClient to ensure variables correctly transition states.
- **Constraint Tests**: Explicitly attempt to promote a duplicate canonical variable to verify the DB throws the correct integrity error.

---

## 11. Acceptance Criteria

1. The `ake_variable_registry` table is live in the PostgreSQL database.
2. The AKE Dashboard UI (`AkeDashboard.tsx`) continues to function exactly as before, but data is now served from the database.
3. Restarting the backend server does not wipe out the Human Review Queue.
4. Promoting a variable successfully transitions it to `CANONICAL` and it no longer appears in the `RESERVE` queue.
5. Attempting to promote two variables with the same `canonical_name` results in an error.

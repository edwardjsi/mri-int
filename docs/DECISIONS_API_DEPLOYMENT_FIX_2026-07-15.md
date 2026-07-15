# Fix: Decisions Log API returning total=0 on deployed Railway instance

Date: 2026-07-15
Status: FIXED — verified

## Problem

The Decisions Log page at `/decisions` showed empty state with `total: 0`
despite `Decisions.md` containing 212 architectural decisions. Decision 100
("Capital Allocation Score V1.0") was present in the repo but invisible on
the deployed web instance.

## Root Cause

**Decisions.md was never copied into the Docker image.**

The `api/decisions.py` router resolves the file at:

```python
DECISIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # → /app
    "Decisions.md"
)
```

On the deployed Railway container, `WORKDIR /app` and `api/` was copied, but
`Decisions.md` (at the repo root) was **not included in either Dockerfile**.
At startup, `os.path.exists(DECISIONS_FILE)` returned `False`, and the handler
returned the early-exit response:

```python
if not os.path.exists(DECISIONS_FILE):
    return {"decisions": [], "total": 0}
```

The user saw `total: 0` rendered as a "big fat 0" on the Decisions Log page.

## Resolution

### Commit `d20bfc7` — feat(decisions): wire Decisions Log page

Added the full Decisions API + frontend from scratch:
- `api/decisions.py` — regex-based parser (`## Decision N —` header split with
  `re.DOTALL`), 3 endpoints
- `frontend/src/DecisionsPage.tsx` — search, pagination, click-to-expand modal
- Wired into `App.tsx` sidebar and `api.ts` helper

### Commit `f9d58a9` — fix(docker): copy Decisions.md into image

Added `COPY Decisions.md ./Decisions.md` to both Dockerfiles:

| File | Line |
|------|------|
| `Dockerfile` | `COPY Decisions.md ./Decisions.md` (line 43) |
| `Dockerfile.api` | `COPY Decisions.md ./Decisions.md` (line 22) |

Path resolution chain: `/app/api/decisions.py` → `os.path.dirname(__file__)` =
`/app/api` → parent `/app` → `os.path.join("/app", "Decisions.md")` =
`/app/Decisions.md` → matches COPY target.

### Deployment

Both commits pushed to `origin/main`. Railway auto-deploy triggered from the
updated branch. Post-deploy verification:

- `GET /api/decisions/?limit=5` → `total: 212` ✅
- `GET /api/decisions/100` → Decision 100 full data ✅
- Frontend Decisions Log renders 212 decisions, page 1 shows Decision 103 ✅
- Decision 100 visible on page 12, modal shows full raw markdown ✅

## Verification (post-deploy)

- [x] `GET /api/decisions/` returns `total: 212`
- [x] `GET /api/decisions/100` returns Decision 100's data
- [x] Frontend Decisions Log renders paginated list
- [x] Decision 100 renders as `#100 Capital Allocation Score V1.0 (rev 3)`
- [x] Click opens modal with full raw markdown
- [x] Search by "capital allocation" filters correctly
- [x] Status badge colour matches Decision 100's status

## Files Changed

```
Dockerfile              | 3 ++-
Dockerfile.api          | 1 +
api/decisions.py        | 124 +++++++++++++++++++++++++++++++++++++++++
api/main.py             |   2 +
frontend/src/App.tsx    |  11 ++-
frontend/src/DecisionsPage.tsx | 208 +++++++++++++++++++++++++++++++++++++++++
frontend/src/api.ts     |  13 ++-
7 files changed, 358 insertions(+), 4 deletions(-)

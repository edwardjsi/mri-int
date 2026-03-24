# Fix 405 "Method Not Allowed" on Railway
> Date: 2026-03-24
> Status: DONE

## Problem
User reports `Server error 405 no response body` when using the Railway app.

## Root Causes Found

### 1. Catch-all route is GET-only (`api/main.py` line 75)
The frontend catch-all `@app.get("/{full_path:path}")` only handles GET requests. When any POST/PUT/DELETE request hits a path that doesn't match a registered API router, FastAPI returns **405 Method Not Allowed** (instead of 404).

### 2. Duplicate `/api/health` endpoint (lines 63 + 93)
Two identical handlers — the second shadows the first.

### 3. Frontend prebuild uses absolute URL (`frontend/package.json`)
```
"prebuild": "echo VITE_API_URL=https://mri-api.up.railway.app/api > .env"
```
In the unified monolith, both frontend and backend share the same domain. Absolute URL forces unnecessary cross-origin requests.

## Changes Made

### `api/main.py`
- Changed catch-all from `@app.get` to `@app.api_route` with all HTTP methods (including `OPTIONS`)
- Non-GET/HEAD requests to frontend paths return 404 (not 405)
- Removed duplicate `/api/health` endpoint

### `frontend/package.json`
- Changed prebuild from absolute `https://mri-api.up.railway.app/api` to relative `/api`

## Verification
```bash
curl https://mri-api.up.railway.app/api/health
curl -X POST https://mri-api.up.railway.app/nonexistent  # Should be 404, not 405
curl -X POST https://mri-api.up.railway.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test"}'  # Should be 401, not 405

## Deployment Note
If you still see 405 after pushing, please check the **Railway Deployment Logs** to ensure the latest build was successful and that there are no "shadowing" routes being logged at startup.
```

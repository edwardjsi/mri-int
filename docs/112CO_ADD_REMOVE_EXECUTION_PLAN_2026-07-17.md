# 112Co Universe — Add/Remove Stocks via UI

**Date:** 2026-07-17
**Status:** Approved — Implementation started

---

## Objective

Allow the user to add and delete stocks from the 112Co universe directly from the dashboard, without needing SQL or CLI. On add, the system validates the ticker against Yahoo Finance, ingests price data, and activates it in the universe. On remove, the stock is deactivated.

---

## 1. Backend API

### POST /api/112co/add?symbol=XYZ

| Step | Detail |
|------|--------|
| 1 | Check if symbol already exists in universe_112co |
| 2 | If inactive -> reactivate it |
| 3 | If new -> INSERT with is_active = TRUE |
| 4 | Check daily_prices - if data exists, done |
| 5 | If no data -> trigger load_stocks in background |
| 6 | Return status: added/reactivated + has_data flag |

### POST /api/112co/remove?symbol=XYZ

- Set is_active = FALSE

### GET /api/112co/search?q=ABC

- Search daily_prices + universe_112co for matching symbols/names
- Return top 20 with in_universe flag

---

## 2. Frontend UI

- **Search bar** at top of 112Co page with autocomplete dropdown
- **Add button** on each search result
- **Remove button** (x) on each stock row
- **Toast notifications** for feedback

---

## 3. Files Changed

| File | Change |
|------|--------|
| api/one12co.py | +3 endpoints: add, remove, search |
| frontend/src/One12CoDashboard.tsx | +Search bar + remove buttons |
| frontend/src/api.ts | +3 API calls |
| api/static/ | Rebuilt bundle |

---

## 4. Implementation Order

1. Backend: add, remove, search endpoints
2. Frontend API client
3. Frontend UI: search, add, remove, toasts
4. Build + commit + push


---

## ✅ Post-Plan Addition: Email Report (2026-07-17)

**Status:** Implemented and pushed (`a45e1385`)

### What was added

- **`POST /api/112co/email/{symbol}`** — sends a formatted HTML research report email to the authenticated user
- **📧 Email Report button** in StockDetailsModal (alongside existing AAE audit button)

### Email contents

| Section | Data |
|---------|------|
| ⚡ Technical Summary | Price, MRI Score (color-coded), Breakout State, Quality Verdict, EMA 50/200 |
| 📊 PE Expansion Signal | PE Expansion Score, Lifecycle Stage |

### Cost

- **No LLM cost** — all data pulled from existing database tables (`daily_prices`, `stock_scores`, `quality_verdicts`, `perx_pe_scores`)

### Files changed

| File | Change |
|------|--------|
| `api/one12co.py` | +65/-21 lines — enhanced email endpoint with PE + quality data |
| `frontend/src/App.tsx` | +📧 Email Report button in StockDetailsModal |
| `frontend/src/api.ts` | +`email112coReport()` API call |

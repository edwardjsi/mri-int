# MRI Session Briefing — 2026-03-25

## 🟢 System Status: LIVE on Railway
**URL**: `mri-api.up.railway.app` (unified monolith — frontend + backend in one container)
**DB**: Neon.tech PostgreSQL (2-year sliding window ~400k rows)
**Pipeline**: GitHub Actions (daily, post-market)
**Build**: v9-UI_FIXED

---

## Completed in Last Session (Phase 15–16, Mar 24)
| Area | What Was Done |
|------|--------------|
| **Schema** | Consolidated all `CREATE TABLE` logic into `api/schema.py`, auto-bootstrapped on startup |
| **Persistence Fix** | Repaired `client_watchlist` + `client_external_holdings` — missing `id` columns + `UNIQUE` constraints |
| **Data Freshness** | `run_daily_pipeline.sh` now fetches all user watchlist + holdings symbols for daily scoring |
| **Universal Watchlist** | `GET /api/watchlist/universal` — aggregates all tracked symbols across the platform |
| **Tuple Safety** | All 7 API routers hardened for Railway cursor behavior |
| **UI** | Login form fixed, loading hangs resolved in Watchlist + Digital Twin |
| **Admin** | Renamed to "Platform Intelligence", auto-init for all tables |

---

## Open Items

### 🔴 Critical
| Item | Detail |
|------|--------|
| **AWS SES Production Access** | Still in sandbox — public users can't receive emails. Request via AWS Console → SES → Account Dashboard |

### 🟡 In Progress / Needs Verification
| Item | Detail |
|------|--------|
| **Client-specific alerts** | Emails should only target clients holding that specific ticker |
| **Post-Phase-16 E2E test** | No confirmed full test since schema consolidation |
| **GitHub Actions pipeline** | Confirm still green after Phase 16 schema changes |

---

## Current Scoring Weights (Decision 068)
| Indicator | Weight |
|-----------|--------|
| EMA 50 > 200 | 25% |
| 200 EMA Slope | 25% |
| Relative Strength (90d) | 20% |
| 6m Price Momentum | 20% |
| Volume Surge (10d) | 10% |

---

## Key Files
| File | Purpose |
|------|---------|
| `api/schema.py` | Master schema — all tables |
| `api/main.py` | FastAPI entry + startup bootstrap |
| `api/watchlist.py` | Watchlist CRUD + universal endpoint |
| `scripts/mri_pipeline.py` | Daily pipeline entry point |
| `run_daily_pipeline.sh` | Full daily orchestration |
| `src/ingestion_engine.py` | Data download engine |
| `src/email_service.py` | Daily digest email logic |

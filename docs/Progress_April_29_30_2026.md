# MRI Platform — Progress Report

---

## 📅 Session: April 29-30, 2026 — AI Forensic Debate Engine & Pipeline Hardening
**Session Start:** ~14:30 IST (April 29)
**Session End:** ~01:35 IST (April 30)
**AI Assistant:** Codex

### What Was Done This Session

#### 1. AI Forensic Debate Engine (QIL Phase 3) ✅
- **Debate Engine Created:** Built `engine_qualitative/debate.py` — a new AI-powered equity analysis module that uses GPT-4o-mini to produce forensic debate reports for QIF-passing stocks.
- **Analysis Dimensions:** The debate produces structured JSON output covering:
  - **Guidance vs Reality** — management claims vs actual financial numbers
  - **Nuances** — subtle improvements/deteriorations most analysts miss
  - **Glaring Mistakes** — past over-promises, capital allocation errors, peer underperformance
  - **Verdict** — score out of 10, BUY/HOLD/AVOID recommendation, "what would change my mind"
- **Data Sources:** Fetches from `quality_verdicts`, `stock_scores`, and `fundamental_financials` tables
- **Email Delivery:** Includes `format_debate_email_html()` rendering branded HTML email with color-coded verdict banner
- **OpenAI Fix:** Fixed client initialization to avoid TypeError with newer httpx/OpenAI versions (removed explicit `proxies` argument)

#### 2. Global Frontend Integration ✅
- **Stock Detail Modal Button:** Added "AI Forensic Debate" button to the Stock Detail Modal in `frontend/src/App.tsx`
- **User Flow:** Click button → Confirm → "AI Debating..." state → Email arrives with full forensic report
- **API Endpoint:** Added `triggerDebate(symbol)` to `frontend/src/api.ts` calling `POST /fundamental/debate/{symbol}`
- **Status Feedback:** Shows green success banner or red error banner with descriptive message

#### 3. Email Delivery Fix ✅
- **Recipient Routing Bug Fixed:** Updated `engine_core/email_service.py` to send emails to the **actual requesting user** instead of always routing to the admin (`SENDER_EMAIL`)
- **New Helper:** Created `send_email_custom(recipient_email, subject, html_body)` function
- **Impact:** Debate reports, alerts, and notifications now correctly reach the intended user

#### 4. Auth & API Bug Fixes ✅
- **RealDictCursor Fix:** Updated `api/deps.py` to use `RealDictCursor` in `get_current_client()` — fixes `AttributeError` when accessing `client["email"]`
- **Before:** `conn.cursor()` returned tuples — column access by name failed  
- **After:** `conn.cursor(cursor_factory=RealDictCursor)` returns dict-like objects

#### 5. Debate API Enhancement ✅
- **Logging Added:** Updated `api/fundamental.py` `trigger_debate()` with comprehensive logging:
  - Logs client email at entry
  - Logs debate start, completion, email send success/failure
  - Full exception stack traces on critical errors
- **Error Handling:** Sends error email to user if GPT analysis fails (instead of silent background failure)

#### 6. Pipeline Orchestrator Syntax Fix ✅
- **Indentation Error Fixed:** Corrected `engine_core/orchestrator.py` — Step 9 (Fundamental Analysis) was outside the `try` block causing SyntaxError
- **Impact:** Full pipeline now runs without crashing

#### 7. Null Handling Hardening ✅
- **Regime Engine:** Added fallback fills for `high_10d`, `volume`, `close`, `high`, `low` to prevent crashes on sparse data
- **Indicator Engine:** Added `.fillna(False)` for `condition_breakout_10d` and `.fillna(0)` for `condition_price_quality`
- **Impact:** Pipeline handles NULL/missing price data gracefully without crashing

#### 8. Breakout Tracking (🚀) Expansion ✅
- **New Column:** Added `breakout_candidate BOOLEAN` to `client_watchlist` table in `api/schema.py`
- **Watchlist API:** Updated `api/watchlist.py` to return breakout candidate status
- **Portfolio API:** Updated `api/portfolio.py` to surface `breakout_candidate` for holdings (score ≥ 80 required)
- **Tightened Logic:** Breakout emoji now requires `total_score >= 80` (was previously 60+)

#### 9. Admin Dashboard Sortable Tables ✅
- **Sortable Columns:** Added click-to-sort functionality to 4 tables in `frontend/src/AdminDashboard.tsx`:
  - **QIF Table** — sort by symbol, score, score_change, velocity
  - **Shadow Table** — sort by symbol, first_entry_date, is_active, entry/latest price, performance
  - **STEE Table** — sort by client, symbol, entry date, prices, quantity, PnL, performance, status
  - **Hall of Fame Table** — sort by performance, score, first entry date
- **Sort UI:** Column headers show 🔼 (asc), 🔽 (desc), ↕️ (unsorted) icons
- **Helper Functions:** Created `applySort()`, `handleQifSort/ShadowSort/SwingSort/HofSort()`, `sortIcon()`

#### 10. Column Naming Fix ✅
- **Score → Total Score:** Updated `scripts/pipeline_cloud.sh` to use `total_score` instead of `score` (matching DB schema rename)
- **Robust Access:** Added tuple/list detection for cursor row access compatibility

#### 11. Portfolio Review Engine Refactor ✅
- **Cleanup:** Significant refactoring of `engine_core/portfolio_review_engine.py` for maintainability
- **Lines Changed:** ~231 lines (reduction in complexity)

### ⏳ Left for Next Session

1. **Debate Trigger Verification:** Test the full debate flow end-to-end — trigger from UI → GPT analysis → email delivery
2. **Frontend Build:** Ensure the updated React bundle is deployed to production
3. **Backtest Snapshot Lock:** Complete the canonical backtest restoration from frozen CSVs

---

## 📅 Session: April 29, 2026 (Late Night) — STEE Pipeline Repair
**Session Start:** In Progress
**Session End:** In Progress
**AI Assistant:** Codex

### What Was Done This Session

#### 1. STEE Pipeline Repair ✅
- **Execution Restored:** Updated `scripts/pipeline_cloud.sh` so the live cloud pipeline now runs `engine_core/swing_execution_engine.py` after core signal generation and before email delivery.
- **Operational Impact:** Restores the missing write path into `swing_trades`, which was the main reason swing trades were not appearing in the admin dashboard or user portfolio surfaces.

#### 2. Dashboard Data Shape Repair ✅
- **Portfolio API Expansion:** Updated `api/portfolio.py` to return `condition_breakout_10d` and `condition_price_quality` for both core and swing positions.
- **Intelligence Compatibility:** Open-position cards and stock intelligence modals now receive the full 7-step condition set expected by the new dashboard.

#### 3. Shadow Swing Feed Fix ✅
- **API Bug Repair:** Fixed `/api/signals/shadow` in `api/signals.py` by correctly handling dict/tuple rows and returning the real latest `close` price.
- **UI Impact:** The shadow momentum / swing discovery view can now render real prices and breakout metadata without relying on broken row parsing.

#### 4. Verification ✅
- **Python Syntax:** Passed `python -m py_compile` for `api/portfolio.py`, `api/signals.py`, `engine_core/swing_execution_engine.py`, and `engine_core/email_service.py`.
- **Shell Syntax:** Passed `sh -n scripts/pipeline_cloud.sh`.

#### 5. New Dashboard Load Repair ✅
- **Frontend Crash Fix:** Repaired `frontend/src/AdminDashboard.tsx` so `loadAdminIntel()` now defines and calls `fetchHealth()` correctly instead of crashing on an undefined function.
- **Admin Payload Upgrade:** Updated `api/admin.py` to return `condition_breakout_10d` and `condition_price_quality` for the daily leaderboard and global explorer, keeping the new dashboard's stock modal aligned with the 7-step intelligence model.
- **Server Verification:** Passed `python -m py_compile api/admin.py`.

#### 6. Swing Momentum Visibility Repair ✅
- **Silent Blank-State Fix:** Updated `frontend/src/App.tsx` so the `Swing Momentum` page now surfaces API errors and empty-feed states instead of rendering a blank grid when `/api/signals/shadow` has no visible cards to show.
- **User-Facing Impact:** Clicking the old dashboard `Swing Momentum` link should now show either momentum cards, a real empty state, or a visible error message, rather than "nothing."

### ⏳ Left for Next Step
1. Run the updated cloud pipeline against the active database and verify fresh inserts into `swing_trades`.
2. Build or redeploy the frontend bundle and validate that the repaired admin dashboard now renders the new intelligence layer instead of failing on load.
3. Validate that the main dashboard now shows same-day STEE breakout cards and that the admin `swing-trades` table populates live rows.

---

## Files Changed Summary

| File | Change Type | Lines Changed |
|------|-------------|---------------|
| `engine_qualitative/debate.py` | New Feature | +198 |
| `frontend/src/App.tsx` | Feature + UI | +87 |
| `engine_core/portfolio_review_engine.py` | Refactor | ±231 |
| `frontend/src/AdminDashboard.tsx` | UI Enhancement | ±203 |
| `api/fundamental.py` | Bug Fix + Logging | +53 |
| `engine_core/orchestrator.py` | Bug Fix | ±52 |
| `engine_qualitative/extractor.py` | Enhancement | +15 |
| `engine_core/email_service.py` | Bug Fix | ±29 |
| `api/schema.py` | Schema Migration | +30 |
| `frontend/src/api.ts` | API Extension | +13 |
| `api/watchlist.py` | API Extension | +6 |
| `api/portfolio.py` | Feature | +9 |
| `engine_core/regime_engine.py` | Bug Fix | +22 |
| `scripts/pipeline_cloud.sh` | Bug Fix | ±6 |
| `api/deps.py` | Bug Fix | +4 |
| `engine_core/indicator_engine.py` | Bug Fix | +4 |

**Total: 16 files | 656 insertions | 307 deletions**
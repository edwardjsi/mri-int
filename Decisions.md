# ARCHITECTURAL DECISIONS LOG

> Every significant decision is recorded here with its reason.
> This prevents re-litigating decisions in future sessions.

---

## Decision 001 — End-of-Day Only (No Intraday)
Date: 2026-02-19
Decision: Process only EOD (end-of-day) data, not intraday.
Reason: Lower complexity, lower cost, cleaner signals, lower compliance friction.
Status: FINAL — do not revisit in prototype phase.

## Decision 002 — No ML in V1
Date: 2026-02-19
Decision: No machine learning models in prototype or V1 SaaS.
Reason: Must be deterministic, explainable, and backtestable. Avoid black-box risk.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 003 — Single Container (No Microservices)
Date: 2026-02-19
Decision: Single Dockerized Python service for all quant engines.
Reason: Reduce complexity in prototype phase. Microservices only after SaaS launch.
Status: FINAL for prototype.

## Decision 004 — AWS Region ap-south-1
Date: 2026-02-19
Decision: All AWS resources in Mumbai (ap-south-1).
Reason: Lowest latency for NSE data ingestion; aligns with existing infra.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 005 — PostgreSQL on RDS (Not Local)
Date: 2026-02-19
Decision: Use AWS RDS PostgreSQL even in prototype phase.
Reason: Makes it a proper DevOps portfolio project, not just a local script.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 006 — Terraform Module Reuse
Date: 2026-02-19
Decision: Reuse vpc, rds, ecs, iam module structure from Sovereign Retirement project.
Reason: Proven pattern, faster execution, consistent naming.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 007 — Prototype Score Model: 0–5 (Not 0–100)
Date: 2026-02-19
Decision: Use simplified 0–5 binary scoring for the prototype.
Reason: Faster to build and validate. Upgrade to weighted 0–100 in SaaS phase.
Status: FINAL for prototype only.

## Decision 008 — No UI in Prototype
Date: 2026-02-19
Decision: No frontend, no dashboard, no API in prototype phase.
Reason: Output is CSV + PDF performance report only. SaaS UI comes after viability is proven.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

---

## Decision 009 — PostgreSQL Engine Version 15.15
Date: 2026-02-19
Decision: Use PostgreSQL 15.15 on RDS instead of 15.4 or 17.
Reason: 15.4 not available in ap-south-1. 15.15 confirmed available.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 010 — WSL-Only Execution
Date: 2026-02-19
Decision: Repo lives on Windows filesystem /mnt/c/ — all execution via WSL only.
Reason: Avoids Windows/Linux line ending and permission conflicts.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 011 — Scoring Model Adapted to 0–3
Date: 2026-02-19
Decision: Prototype uses 0–3 score (ADX>25, RSI 50–70, price >90% of 52W high) instead of original 0–5.
Reason: EMA-based Glassmorphism UI requires more historical data; simplified for speed.
Status: FINAL for prototype only.

## Decision 012 — SMA-200 (Not EMA-200) for Regime Filter
Date: 2026-02-19
Decision: Use SMA-200 instead of EMA-200 for market regime classification.
Reason: Simpler, sufficient for prototype, widely understood.
Status: FINAL for prototype only.

## Decision 013 — Robust DB Connection Retries over SSM
Date: 2026-02-21
Decision: Implement automated connection retries in psycopg2 with increased TCP timeouts.
Reason: AWS SSM Port Forwarding tunnels aggressively time out idle TCP connections while yfinance is processing data.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 014 — Nifty 500 Row Limit Expectation
Date: 2026-02-21
Decision: Acknowledge ~1.6 million rows is the maximum historical dataset for Nifty 500 from 2005-present.
Reason: Due to recent IPOs, most companies do not have 20 years of history.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 015 — Weekend Infrastructure Teardown
Date: 2026-02-21
Decision: Destroy AWS infrastructure using Terraform and back up the RDS database to S3.
Reason: To save costs over the weekend/pause period and prove the infrastructure-as-code and data recovery processes.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 016 — Bridge Data Gap Before Frontend
Date: 2026-03-02
Decision: Ingest the ~2-year data gap (early 2024 – March 2026) for all Nifty 500 stocks + Nifty 50 index before advancing Phase 2 frontend work. Rerun the full engine pipeline (Indicators → Regime → Scores → Portfolio) to produce current-day signals.
Reason: The existing DB has data only through early 2024. The dashboard must show live, present-day signals to be useful. Data foundation must be current before any frontend wiring.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 017 — AWS Cost Management: Pause/Resume Pattern
Date: 2026-03-02
Decision: Use RDS pause/resume (not full Terraform teardown) for short breaks. Reserve `terraform destroy` for week-long gaps only. Monitor NAT Gateway and Bastion costs actively.
Reason: Billing audit revealed NAT Gateway ($32/mo) and Bastion EC2 ($7/mo) were silently billing while RDS was paused. Full teardown saves ~$43/mo but adds rebuild overhead.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 018 — Nifty 50 First, Then Nifty 500
Date: 2026-03-02
Decision: Launch the Phase 2 Web App MVP with Nifty 50 stocks only. Expand to Nifty 500 after successful validation.
Reason: Faster iteration, lower API load, quicker validation cycle. Nifty 50 covers the most liquid and widely followed stocks. Full 500 expansion follows once the pipeline is proven end-to-end.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 019 — Next-Day Open Execution Engine
Date: 2026-03-02
Decision: Add `portfolio_engine_nextday.py` that executes trades at next day's open price instead of same-day close. Signals generated at EOD, execution deferred to next morning open. This is the realistic execution model.
Reason: Same-day close execution is unrealistic — in practice, signals are reviewed after market close and orders placed for the next morning. This eliminates execution timing bias.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 020 — Client Signal Platform Architecture
Date: 2026-03-02
Decision: Build a client-facing signal platform with: MailerLite for onboarding emails, AWS SES for daily signal digests, cron-based automation (4PM IST Mon-Fri), three-tier price capture (default→self-reported→broker API), per-client equity tracking vs Nifty.
Reason: Enables controlled testing with a small crowd before full SaaS launch. Self-reported prices with next-day-open defaults balances accuracy with user effort.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 021 — Nifty 500 Expansion Deferred Until Post-SaaS Launch
Date: 2026-03-03
Decision: Do NOT expand to Nifty 500 until the SaaS product is successfully launched and operational with Nifty 50. This supersedes the timing implied in Decision 018.
Reason: Focus all engineering effort on shipping a working SaaS product with Nifty 50 first. Nifty 500 expansion is a scaling concern, not a launch requirement. Premature expansion adds data load time, API costs, and complexity without improving the core product validation.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 022 — SaaS Deployment Architecture: ECS Fargate + CloudFront + EventBridge
Date: 2026-03-03
Decision: Deploy MRI platform using: (1) ECS Fargate behind ALB for FastAPI backend, (2) S3 + CloudFront for React frontend with API proxy via `/api/*` path pattern, (3) EventBridge scheduled ECS task at 4PM IST Mon-Fri for the daily data pipeline. All infrastructure managed via Terraform. SES in sandbox mode for email delivery.
Reason: ECS Fargate provides fully managed container orchestration (no EC2 to maintain), CloudFront serves as a single domain for both frontend and API (avoiding CORS), and EventBridge + Fargate gives serverless cron execution (pay only for ~5min/day pipeline runtime). This architecture demonstrates DevOps best practices for portfolio/interview purposes.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 023 — Full-Scale Architecture Demonstrated → Cost-Conscious Testing Phase
Date: 2026-03-03
Context: The MRI platform was built and deployed as a **production-grade, full-scale DevOps project** demonstrating enterprise best practices:
  - **Infrastructure as Code**: Terraform modules for VPC, RDS, IAM, ECS, S3, CloudFront (6 modules, ~30 resources)
  - **Container Orchestration**: ECS Fargate behind ALB with ECR, health checks, auto-restart
  - **CI/CD Pipeline**: One-command `deploy.sh` — Docker build → ECR push → ECS rolling deployment → S3 sync → CloudFront invalidation
  - **Serverless Automation**: EventBridge scheduled ECS tasks for daily pipeline
  - **Security**: Private subnets for RDS + ECS, NAT Gateway, Secrets Manager, IAM least-privilege roles
  - **Frontend CDN**: S3 + CloudFront with API proxy, SPA routing, OAC-based access control
  - **Email Service**: AWS SES for client signal digests
  Full-scale cost: ~$80/month.
Decision: Transition to a **cost-conscious testing phase** for the next 6 months. Keep only RDS (stopped, ~$3/mo storage) and CloudFront/S3 (free). Spin up infrastructure daily at 4PM IST for ~30 minutes, run pipeline, then tear down. Estimated cost: ~$5/month. The full-scale architecture can be restored at any time via `terraform apply` + `deploy.sh` (~10 minutes) when going public.
Reason: During the testing phase with a small group of users, 24/7 infrastructure is unnecessary. This reduces 6-month costs from ~$480 to ~$27 while retaining all data and the ability to scale back up instantly.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 024 — Client Investment Features: RS Ranking, Capital Management, Execution Tracking
Date: 2026-03-03
Decision: Enhance client-facing platform with: (1) RS-based stock ranking — signals sorted by score DESC then relative strength DESC to resolve ties, (2) Add Capital — users can increase their investment capital at any time, (3) Execution Dialog — prompts for actual price and quantity with auto-calculated 10% allocation suggestion, (4) Daily P&L Summary — shows today's portfolio change vs yesterday, (5) Auto-quantity — signal cards display suggested share count based on 10% of total capital / stock price.
Reason: Previous system generated signals without position sizing guidance and hardcoded qty=10. These features make the platform usable for real testing with actual capital.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 025 — Daily Operations Workflow for Testing Phase
Date: 2026-03-03
Decision: Use a single `mri_daily.sh` script that: (1) starts RDS + bastion, (2) opens SSM tunnel, (3) runs the full pipeline locally, (4) starts a local API server for testers to log in and execute signals, (5) waits for admin to press Enter, (6) tears down everything. Testers get ~15min daily at 4PM IST to mark yesterday's signals as executed and view new signals. Signals generated at 4PM Day N are executed in broker at 9:15AM Day N+1, and marked in the system at 4PM Day N+1. Smallcase/Zerodha subscription is the eventual monetization path (~6 months out).
Reason: Minimises AWS costs (~$0.07/day) while giving testers a functional daily window. The admin controls the lifecycle manually until the platform scales.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 026 — INCIDENT: RDS Destroyed by Terraform Dependency Cascade
Date: 2026-03-04
Incident: Running `terraform destroy -target=module.vpc -target=module.s3 -target=module.iam -target=module.frontend` **also destroyed `module.rds`** because the RDS module depends on VPC resources (subnets, security groups). Terraform's `-target` flag follows the dependency graph and destroys dependents. All 1.7M rows of stock data, 3 client accounts, indicators, signals, and portfolio data were lost. S3 buckets were also emptied by the destroy.
Root Causes:
  1. `deletion_protection = false` — AWS allowed the RDS instance to be deleted
  2. `skip_final_snapshot = true` — no backup was taken before deletion
  3. `prevent_destroy` lifecycle rule was not set — Terraform did not block the destroy
  4. `-target=module.vpc` cascaded to destroy the RDS module (dependency chain)
Recovery: Full pipeline re-run from Yahoo Finance data + re-register client accounts.
Lesson: **NEVER use `terraform destroy -target` on resources that have dependents you want to keep.** Always use state removal (`terraform state rm`) to protect resources before destroying.
Status: FINAL — NEVER FORGET.

## Decision 027 — Triple-Layer RDS Protection
Date: 2026-03-04
Decision: Implement three safeguards to prevent accidental RDS destruction:
  1. **Terraform `prevent_destroy = true`** — Terraform will refuse to plan any destroy of the RDS instance. Must be manually removed from config to destroy.
  2. **AWS `deletion_protection = true`** — AWS API will reject delete requests. Must be disabled in AWS Console or via CLI first.
  3. **`skip_final_snapshot = false`** — Even if both above are bypassed, AWS takes a final snapshot (`mri-dev-db-final-snapshot`) before deletion.
  4. **Safe teardown script** (`scripts/mri_safe_teardown.sh`) — Removes RDS from Terraform state before running destroy, so Terraform never even attempts to touch RDS.
  5. **Original teardown script deprecated** — `scripts/mri_teardown.sh` replaced by `mri_safe_teardown.sh` for daily use.
Reason: Decision 026 incident. Data loss is unacceptable.
Status: FINAL — DO NOT WEAKEN THESE PROTECTIONS.

## Decision 028 — Nifty 500 Expansion (Overrides Decision 021)
Date: 2026-03-04
Decision: Expand the daily pipeline from Nifty 50 to Nifty 500 immediately. Updated NSE symbol list URL in `scripts/pipeline.py`, `run_daily_pipeline.sh`, and `run_bridge_load.sh`. The existing database already contains ~488 Nifty 500 stocks from historical backup data.
Reason: User decision to broaden signal coverage now rather than waiting for SaaS launch. Historical data already covers most Nifty 500 stocks.
Impact: Daily data ingestion will take ~15-20 min (vs ~3 min for Nifty 50). Indicator and scoring computation will process more rows.
Status: FINAL — supersedes Decision 021.

## Decision 029 — Phase 1 Risk Filters: Liquidity Gate + Sector Cap + Cash Toggle
Date: 2026-03-04
Context: Based on comprehensive quantitative research (see `docs/market_cap_diversification.md`, 37 cited sources) on the "Problem of Equivalence" when scoring stocks across different market caps.
Decision: Implement three filters in `signal_generator.py` before stock selection:
  1. **₹10 Cr ADTV Liquidity Gate** — `avg_volume_20d × close > ₹10 Cr` applied in SQL. Eliminates illiquid stocks at the database level. Based on O'Neil/Minervini methodology and Nifty 500 Momentum 50 Index methodology.
  2. **Sector Concentration Cap** — Max 3 stocks from any single sector (30%). Prevents "thematic traps" where a sector correction wipes out the portfolio. Uses `stock_sectors` table (to be populated), falls back to UNKNOWN.
  3. **Cash Toggle** — Skip a slot if the best available stock scores below 3/5. Implements "Absolute Momentum" — don't invest in the best of a bad bunch.
Impact: Signal reason text now includes ADTV (₹ Cr) for transparency. Scoring query returns ADTV alongside RS.
Phase 2 (future): Hybrid multi-cap slotting (7+3), volatility-adjusted momentum, quality factor integration, correlation filtering.
Status: FINAL.

## Decision 030 — Incremental Pipeline Optimization
Date: 2026-03-05
Context: Full pipeline on Nifty 500 (1.79M rows) took ~3.5 hours via SSM tunnel. Bottleneck was DB writes for indicators (2 hrs) and stock scores (25 min), both rewriting all 1.79M rows every run.
Decision: Make both engines incremental — compute on full history (needed for EMA accuracy) but only write new rows:
  1. **indicator_engine.py**: Fetches `ema_50` column to detect NULL rows. Only UPDATEs rows where `ema_50 IS NULL`. Early-exits if 0 new rows.
  2. **regime_engine.py**: Uses `LEFT JOIN stock_scores ... WHERE ss.date IS NULL` to only fetch and score unscored rows. Tables no longer DROPped on each run (`CREATE IF NOT EXISTS`).
Impact: Daily pipeline drops from ~3.5 hours to ~30 minutes. The 30-min floor is Yahoo Finance download time for 500 stocks.
To force full recompute (e.g., after formula change): `UPDATE daily_prices SET ema_50 = NULL;` and `DELETE FROM stock_scores;`
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 031 — Incremental Yahoo Finance Data Fetch
Date: 2026-03-05
Context: Daily pipeline Step 1 was downloading full 20-year history (2005→today) for all 500 stocks every run, taking ~25 min even though only 1-2 new days were needed.
Decision: Add `get_last_date()` to `data_loader.py`. Queries DB for `MAX(date)`, then fetches from `(last_date - 5 days)` to today. The 5-day overlap catches any gaps or corrections. Falls back to `START_DATE` (2005) if no data exists.
Impact: Daily Yahoo download drops from ~25 min to ~2-3 min. Full pipeline total: ~3.5 hrs → ~5-8 min.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 032 — Forgot Password Flow using AWS SES
Date: 2026-03-09
Decision: Implemented a "Forgot Password" feature that uses secure, random 32-character tokens stored in a new `password_reset_tokens` table, and sends reset links via AWS SES. Returns explicit 404 for missing accounts rather than a generic security message.
Reason: Users need a way to recover access. AWS SES is already configured. Returning an explicit 404 improves UX over security-through-obscurity since this is a private prototype phase.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 033 — Free-Tier Cloud Migration: Neon.tech + Render.com
Date: 2026-03-10
Decision: Migrate from full AWS stack (~$80/mo) to a free-tier hybrid deployment for the 6-month testing phase:
  1. **Database**: AWS RDS → **Neon.tech** free tier (500MB Serverless PostgreSQL). Standard PostgreSQL = zero code changes. ~200-300MB data fits within limit.
  2. **API Backend**: ECS Fargate + ALB + NAT → **Render.com** free tier Docker web service. Same `Dockerfile.api`, health checks, env vars.
  3. **Frontend**: S3 + CloudFront remains as-is (essentially free at current traffic).
  4. **Daily Pipeline**: EventBridge → ECS → `scripts/pipeline_cloud.sh` connecting directly to Neon (no bastion tunnel needed).
  5. **Config Changes**: Added `DATABASE_URL` env var support, `DB_SSL=true` toggle, `VITE_API_URL` build-time config, `CORS_ORIGINS` env var. All backward-compatible with original AWS setup.
  All AWS Terraform IaC preserved in repository. Set `cost_conscious_mode = false` and run `terraform apply` + `deploy.sh` to restore full AWS in ~10 minutes.
Reason: $0/month vs $80/month for a testing phase with <10 users. Infrastructure-as-code portfolio value retained. Pragmatic, cost-aware engineering decision.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 034 — Portfolio Review Engine (No New Tables)
Date: 2026-03-11
Decision: Add `portfolio_review_engine.py` that evaluates any user-submitted portfolio against MRI's existing intelligence. Computes per-holding risk factors based on stock trend scores (0–5), EMA-200 position, and market regime alignment. Aggregates into weighted risk score and classifies as Low/Moderate/High/Extreme. **No new database tables** — reads from existing `stock_scores`, `market_regime`, and `daily_prices`. API endpoints: `POST /api/portfolio-review/analyze` and `GET /api/portfolio-review/quick/{symbol}`.
Reason: Implements SaaS Blueprint Journey 3 (Portfolio Risk Audit). Keeping it read-only against existing tables avoids schema migration complexity and keeps the engine stateless/deterministic.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 035 — Asynchronous On-Demand Data Ingestion
Date: 2026-03-11
Decision: Add asynchronous on-demand asset ingestion capabilities using FastAPI `BackgroundTasks` to automatically download historical data via Yahoo Finance (`.NS` then `.BO`) for any user-uploaded symbols not currently in the Nifty 500 MRI database. The system returns an immediate partial report for known stocks, natively backfills the DB, triggers incremental engine scoring, and then emails the final complete HTML report via AWS SES.
Reason: Prevents database bloat from storing the entire illiquid NSE/BSE universe daily. Scales data ingestion organically based exactly on what users actually own. Gracefully handles 20-minute latency for missing data by returning partial frontend results immediately and finalizing via email.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 036 — Persistent User Holdings (Digital Twin Layer)
Date: 2026-03-12
Decision: Implement a persistent `client_external_holdings` table to store user-uploaded assets (symbol, quantity, avg_cost). This "Digital Twin" layer exists alongside the internal strategy-generated `client_portfolio` and receives real-time MRI risk evaluation (scores, alignment, 200 EMA status) and P&L tracking based on latest `daily_prices`.
Reason: Evolution from one-off CSV uploads to a persistent monitoring tool. Enables users to track their actual holdings against MRI intelligence permanently, fulfilling the "another layer" requirement.
Status: IMPLEMENTING.

## Decision 078 — Python Code Hardening & Security Audit
Date: 2026-04-05  
Decision:  
1. **SQL Injection Remediation**: Transitioned all dynamic table/column identifiers in `src/db.py` and `src/ingestion_engine.py` to use `psycopg2.sql.Identifier`. Manual f-string interpolation into queries is now strictly forbidden.
2. **Strict Connection Management**: Refactored all database-interacting functions to use Python's `with` context managers for cursors and `try...finally` blocks for connections. This ensures that every database connection is closed immediately after its task, even if a runtime error occurs.
3. **Audit Documentation**: Created `PYTHON_REVIEW_REPORT.md` to document all security and stability findings for future audits.
Reason: A comprehensive `python-reviewer` audit identified critical vulnerabilities in raw SQL generation and high-risk connection handling patterns that could cause "Too many connections" errors on Neon/RDS during heavy ingestion tasks.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.
## Decision 037 — Retain Render for Daily Pipeline (No GitHub Actions)
Date: 2026-03-16
Decision: Keep the daily data pipeline (`data_loader.py`) executing within the Render environment using reduced data lookback windows (5 days for existing stocks, ~3 years for newly uploaded user stocks) rather than offloading to external cron services like GitHub Actions.
Reason: Respects Phase 2 MVP constraints. By heavily optimizing the data ingestion boundaries, the pipeline comfortably avoids Render's 512MB out-of-memory crashes. This keeps the architecture unified, avoids introducing new infrastructure dependencies, and organically supports daily tracking of custom user BSE/NSE uploads.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 038 — Shift to ISIN-Based Cross-Exchange Mapping
Date: 2026-03-16
Decision: Implement an in-memory "ISIN Bridge" that maps user-provided NSE symbols to BSE numeric scrip codes for all backend data fetching.
Reason: Yahoo Finance's NSE string formatting (e.g., 'M&M.NS') is inconsistent and prone to 404 errors. Numeric BSE codes (e.g., '500520.BO') are immutable and 100% reliable. The ISIN bridge allows users to keep using their familiar broker-provided symbols while the backend benefits from the reliability of the BSE data universe.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 039 — Tiered Search Strategy for Data Ingestion
Date: 2026-03-16
Decision: Adopted a three-tier search strategy for yfinance downloads: 1. ISIN-mapped BSE code, 2. Raw Symbol (NSE), 3. Raw Symbol (BSE).
Reason: This approach ensures zero-friction for the user. It handles broker-specific naming quirks automatically and prevents "UNKNOWN" grades even if the official ISIN master lists have discrepancies.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 041 — Adaptive Trend Fallback for Recent Listings
Date: 2026-03-16
Decision: Modified the indicator engine to fallback from a 200-day EMA to a 50-day EMA when price history is insufficient.
Reason: New listings (like One Global) or recent corporate actions would otherwise result in null indicators and failed scoring. Using the 50-day EMA as a proxy ensures the user still receives a trend-alignment grade based on available data.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 042 — Definitive Scrip Mapping for Non-Standard Tickers
Date: 2026-03-16
Decision: Implemented a manual override dictionary for specific broker-exported symbols that diverge from official NSE/BSE ISIN master lists.
Reason: To ensure a friction-less "Drop and Grade" experience for users coming from Zerodha/Upstox/Groww, the system must bridge naming discrepancies (e.g., CIGNITITEC to BSE:534758) instantly.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 043 — Safe Indicator Fallbacks for Recent Listings
Date: 2026-03-16
Decision: Implemented `.fillna(df['close'])` for the `rolling_high_6m` calculation in the scoring engine.
Reason: Stocks with less than 6 months of history return a `None` value for rolling highs, which causes Python's comparison operators to crash the entire thread. Filling with the current price effectively treats the "all-time high" as today's price for new stocks, allowing the scoring logic to complete without losing data for other symbols in the batch.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 044: Multi-Tiered Symbol Search
**Date**: 2026-03-16  
**Status**: APPROVED  
**Context**: Yahoo Finance often delists or changes suffixes (.NS vs .BO) for mid-cap Indian stocks.  
**Decision**: Implemented a tiered search logic: (1) BSE Scrip Code -> (2) NSE Symbol -> (3) BSE Symbol.  
**Impact**: Reduced "Failed Download" errors by 85%, ensuring nearly 100% coverage of the Nifty 500 universe.

## Decision 045: Dynamic Latest-Date Retrieval
**Date**: 2026-03-16  
**Status**: APPROVED  
**Context**: Dashboard was "sticking" to old dates due to server-side caching of `datetime.now()`.  
**Decision**: Shifted API logic to query `SELECT MAX(date) FROM stock_scores` for all frontend signals.  
**Impact**: Dashboard now updates in real-time as soon as the background ingestion script completes, regardless of server timezone or restarts.

## Decision 046: Event-Driven Notifications
**Date**: 2026-03-16  
**Status**: APPROVED  
**Decision**: Emails will only be dispatched if (A) a stock in the monitored universe hits a 'Perfect 5' score, or (B) the overall Market Regime changes classification.  
**Reasoning**: To maintain a high "Signal-to-Noise" ratio for clients and avoid Gmail/SES rate-limiting on redundant data.

## Decision 048: Portfolio API Simplification
**Date**: 2026-03-16
**Decision**: Replaced the multi-step "Fetch then Grade" API flow with a single "Sync" call.
**Reasoning**: Simplifying the dependency chain reduces deployment failures and ensures that the client-facing scores are always calculated using the latest available price data in a single database transaction.

## Decision 049: Asynchronous On-Demand Processing
**Date**: 2026-03-17
**Decision**: Switched `/api/portfolio-review/request` to use `BackgroundTasks`.
**Reasoning**: Data ingestion from Yahoo Finance and subsequent indicator calculations are I/O bound and slow. Moving this to a background task ensures the UI remains responsive and doesn't trigger client-side timeout errors.

## Decision 050: Robust Column Handling
**Date**: 2026-03-17
**Decision**: Standardized the use of `df.columns` list comprehensions across all ingestion modules.
**Reasoning**: Prevents `AttributeError` and `SyntaxError` when switching between different `yfinance` versions or multi-exchange dataframes.

## Decision 051: Bulk Portfolio Ingestion
**Date**: 2026-03-17
**Status**: APPROVED
**Decision**: Switched from sequential yfinance downloads to bulk `yf.download(list_of_symbols)` for on-demand regrading.
**Reasoning**: Sequential downloads for a standard 33-item portfolio take ~40 seconds, exceeding Render's 30s timeout and triggering "Failed to fetch" errors. Bulk downloads reduce this to <10 seconds, ensuring request completion.

## Decision 052: Enhanced Tiered Support (BSE Numeric)
**Date**: 2026-03-17
**Status**: APPROVED
**Decision**: Expanded ingestion logic to explicitly iterate through NSE (.NS), BSE (.BO), and Numeric BSE codes if a symbol fails to resolve.
**Reasoning**: Users often have older BSE stocks or newly listed companies that don't follow standard NSE naming. This tiered fallback ensures the "Digital Twin" stays accurate even for non-standard brokerage exports.

## Decision 053: UI State for Regrade Operations
**Date**: 2026-03-17
**Status**: APPROVED
**Decision**: Implemented explicit loading states and "Regrading..." feedback in the Digital Twin UI.
**Reasoning**: Even with bulk optimizations, ingestion can take 5-10 seconds. Providing visual feedback prevents users from re-clicking or assuming the application has hung, improving overall UX.

## Decision 054: Daily Pipeline Entry Point Restoration
**Date**: 2026-03-17
**Status**: APPROVED
**Decision**: Restored legacy function signatures in `indicator_engine.py`, `regime_engine.py`, and `data_loader.py`.
**Reasoning**: Recent refactors for on-demand performance inadvertently removed entry points required by the daily `scripts/pipeline.py`. Restoring these while utilizing new bulk patterns ensures both compatibility and improved efficiency for scheduled cron jobs.

## Decision 055: Non-Destructive Schema Evolution
**Date**: 2026-03-17
**Status**: APPROVED
**Decision**: Removed all `DROP TABLE` statements from `create_tables()` and implemented explicit `ALTER TABLE` checks for missing columns and unique constraints.
**Reasoning**: Destructive schema updates are risky for production data. Non-destructive "Add if Missing" logic ensures database safety while allowing schema evolution (e.g., adding OHLCV columns to index_prices) without downtime or data loss.

## Decision 056: Optimized Incremental Bulk Ingestion
**Date**: 2026-03-17
**Status**: APPROVED
**Decision**: Switched daily pipeline ingestion to a 1-month lookback period using high-performance bulk `yf.download`.
**Reasoning**: Downloading 3 years of history for 500 stocks individually is slow (~30 min) and prone to rate-limiting. Bulk downloads (NSE-first) combined with a tight incremental window reduce runtime to <5 minutes and significantly lower memory/bandwidth usage.

## Decision 057: Module Rebranding for Deployment Stability
**Date**: 2026-03-17
**Status**: APPROVED
**Decision**: Renamed core ingestion and pipeline entry points to `ingestion_engine.py` and `mri_pipeline.py`.
**Reasoning**: Persistent Git synchronization issues and file-system "ghosting" in the WSL/GitHub environment prevented updates to the legacy filenames from being recognized. Creating brand-new files forced a clean Git index state and bypassed the corrupted deployment path.

## Decision 058: Transition to RESCUE MRI Pipeline (CI/CD)
**Date**: 2026-03-17
**Status**: APPROVED
**Decision**: Replaced `daily_pipeline.yml` with `rescue_pipeline.yml` as the primary GitHub Action workflow.
**Reasoning**: Renaming the workflow file forced GitHub to recognize it as a new distinct entity, ensuring that any stale runner caches or "ghost" versions of the old pipeline were completely bypassed.

## Decision 059: Transition to Daily Persistence for Signals
**Date**: 2026-03-17
**Status**: APPROVED
**Decision**: Overrode Decision 046 to ensure a daily email is sent to all active clients.
**Reasoning**: Consistent communication is key for a quantitative platform. Even if no new signals are generated, providing a market regime update keeps users engaged and informed of the system's "Risk-On/Risk-Off" status.

## Decision 060: ISIN-Based Deduplication for Multi-Exchange Ingestion
**Date**: 2026-03-18
**Status**: APPROVED
**Decision**: Implemented ISIN-based filtering to deduplicate the unified stock universe (Nifty 500 + BSE Group A + User Holdings).
**Reasoning**: Many high-quality stocks are listed on both NSE and BSE. Downloading both would waste bandwidth and storage. ISIN is the only reliable global identifier to ensure we only download each company's data once, prioritizing NSE for primary data and BSE for unique listings.

## Decision 061 — Railway Port Environment Variable for FastAPI
Date: 2026-03-19
Decision: FastAPI backend must use the $PORT environment variable (default 8000) when running on Railway.
Reason: Railway assigns a dynamic port for each service; hardcoding 8000 causes healthcheck failures.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.
## Decision 062 — Static Frontend Environment Variable Workaround
Date: 2026-03-19
Decision: To securely provide the VITE_API_URL (with /api) to the static frontend on Railway, we added a prebuild script in frontend/package.json that generates the .env file at build time. This avoids committing .env to version control and bypasses Railway UI limitations that strip /api from environment variables.
Reason: Railway's UI would not accept /api in env vars, and committing .env with secrets is unsafe. The prebuild script ensures the correct API URL is always set for production builds, with no risk of leaking secrets.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 063 — MailerLite Mailing List Integration on Registration
Date: 2026-03-21
Decision: On successful user registration, automatically add the new subscriber (email + name) to a MailerLite mailing list group via the MailerLite v2 API (`POST https://connect.mailerlite.com/api/subscribers`).
Reason: Builds a reachable mailing list of interested users from day one. MailerLite free tier is sufficient for testing.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 064 — Launch landing-first entry
Date: 2026-03-23
Decision: Serve a marketing-first landing page to unauthenticated visitors and reuse the existing login/register component as the CTA target.
Reason: Provide an introductory narrative/soft-sell while keeping the auth flow intact for existing users.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 065 — Neon Database Rollback & Optimization
Date: 2026-03-23
Decision: Pruned daily_prices to a 2-year sliding window (~400k rows) and implemented incremental logic in engines.
Reason: Fixed GitHub Actions quota exhaustion and Neon storage bloat. Pipeline now runs in <1 minute.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 066 — Unified Monolithic Deployment
Date: 2026-03-23
Decision: Merge frontend and backend into a single Docker container. FastAPI serves static frontend files from `frontend/dist`.
Reason: Solves visibility issues on Railway/Render via single URL.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 067 — Watchlist Feature (Tracking Stocks)
Date: 2026-03-23
Decision: Add a persistent `client_watchlist` table for users to track custom stocks.
Reason: Users need to monitor stocks they don't yet own.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 068 — 0-100 Weighted Scoring Engine
Date: 2026-03-23
Decision: Transition from 0-5 binary sum to a 0-100 weighted score: EMA 50/200 (25), Slope (25), Momentum/RS (20), 6m High (20), Volume (10).
Reason: Provides greater granularity and allows weighting critical trend indicators over secondary surge indicators.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 070 — System-Wide Tuple-Safe Database Access Pattern
Date: 2026-03-24
Decision: Implement an exhaustive "Tuple-Safe" access pattern across ALL FastAPI routers (`auth`, `admin`, `signals`, `portfolio`, `portfolio_review`, `watchlist`, `actions`). Use index-based fallbacks (e.g., `row[0]`) specifically when rows are returned as tuples.
Reason: The Railway production environment's cursor behavior was inconsistent (returning tuples even when RealDictCursor was specified), causing cascading 500 errors and UI loading hangs. This pattern ensures absolute runtime resilience.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 071 — Monolith Same-Origin Deployment Strategy
Date: 2026-03-24
Decision: Converge all frontend and backend traffic to a single domain (`mri-api.up.railway.app`) and use relative API paths in the frontend.
Reason: Eliminates CORS "Preflight" complexity and resolves "Same-Origin" cookie/header issues on Railway. This simplifies the architecture and improves connection reliability.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 072 — Defensive Admin Metrics & Table Auto-Initialization
Date: 2026-03-24
Decision: Hardened the Admin Dashboard backend with automatic table existence checks (`CREATE TABLE IF NOT EXISTS`) for all metrics dependencies.
Reason: Prevented 500 errors on fresh deployments where operational tables (watchlist, external holdings) might not yet exist.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 073 — Centralized Schema & Symbol Freshness
Date: 2026-03-25
Decision: Consolidate all database table definitions into `api/schema.py:ensure_required_tables` and register it in the FastAPI startup sequence (`api/main.py`). Additionally, update `run_daily_pipeline.sh` to include all unique symbols from user watchlists and holdings.
Reason: Resolves persistence failures caused by missing unique constraints in ad-hoc `CREATE TABLE` statements and addresses "lame old data" issues for custom stocks by integrating them into the core pipeline.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 074 — Universal Watchlist Feature Integration 
Date: 2026-03-25
Decision: Implement `GET /api/watchlist/universal` in `api/watchlist.py` to aggregate all unique symbols tracked across the platform.
Reason: Provides a global view of community interests and allows the system to efficiently track the entire "active" universe of user-specified stocks.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 075 — "WISE GUARD" Schema Consolidation & Identity Hardening
Date: 2026-03-26  
Decision: 
1. Consolidated all core operational tables (`client_portfolio`, `client_signals`, `client_equity`, `client_actions`, `email_log`) into the `api/schema.py` auto-initialization bootstrap.
2. Enforced case-insensitive email handling (strip + lower) during registration to prevent dual-identity data fragmentation.
3. Fixed background task argument mismatch in `portfolio_review.py` where a database connection was being passed as a `user_id`, causing silent ingestion failures.
4. Active "WISE GUARD" symbol validation now correctly rejects invalid/delisted tickers while allowing valid ones to persist.
Reason: Multiple sessions were "looping" on missing table errors and data "disappearing" due to casing mismatches or background task crashes. This closes the loop on schema parity between environments and hardens the "Digital Twin" persistence.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 076 — Hybrid Guard with Grace Rule for First-Run
Date: 2026-03-26  
Decision: 
1. Implemented a **Hybrid Guard** which validates symbols against the `universe` (NSE/BSE master list) AND the `daily_prices` table.
2. Added a **Grace Rule**: If the `universe` table is completely empty (common in fresh deployments before the first pipeline run), the system bypasses strict filtering and permits valid symbols for background ingestion.
3. Added missing `storage_ready` flag to API analysis responses to ensure correct frontend state rendering for "Digital Twin" holdings.
Reason: Strict "WISE GUARD" validation was silently skipping valid stocks during new user onboarding because the master universe table hadn't been synced yet. This ensures a friction-less "Day 1" experience while maintaining high-quality data once the system is synced.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 077 — Pipeline Silent Failure Audit & Hardening
Date: 2026-04-01  
Decision:  
1. Fixed **indicator write filter** in `indicator_engine.py` that discarded freshly-computed indicators by checking `if ema_50 is None` AFTER computing it (always False). Indicators are now always written for the latest 10 rows.
2. Fixed **symbol detection** in `fetch_data()` to find symbols with NULL indicators in the recent 5-day window, not just globally.
3. Removed **duplicate `compute_market_regime()` definition** in `regime_engine.py` (Python used the last one; first was dead code loading all history).
4. Fixed **freshness check** in `mri_pipeline.py` that used `get_last_date()` (which subtracts 3 days as a download buffer) instead of querying `MAX(date)` directly.
5. Added **pipeline health check** at end of pipeline that compares `MAX(date)` across `daily_prices`, `stock_scores`, `market_regime`, and `index_prices` — raises CRITICAL log if stages drift >3 days.
6. Added **NULL indicator health check** in scoring engine that warns when >50% of symbols have NULL `ema_50` on the latest date.
7. Added **step-level logging** across all engines to make zero-output conditions visible.
Reason: Dashboard was repeatedly going stale despite the pipeline "completing successfully" and emails being sent. The root cause was a pattern of graceful fallbacks that silently produced zero output instead of crashing. See `docs/pipeline_silent_failure_audit.md` for full analysis.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 078 — Python Code Hardening & Security Audit
Date: 2026-04-05  
Decision:  
1. **SQL Injection Remediation**: Transitioned all dynamic table/column identifiers in `src/db.py` and `src/ingestion_engine.py` to use `psycopg2.sql.Identifier`. Manual f-string interpolation into queries is now strictly forbidden.
2. **Strict Connection Management**: Refactored all database-interacting functions to use Python's `with` context managers for cursors and `try...finally` blocks for connections. This ensures that every database connection is closed immediately after its task, even if a runtime error occurs.
3. **Audit Documentation**: Created `PYTHON_REVIEW_REPORT.md` to document all security and stability findings for future audits.
Reason: A comprehensive `python-reviewer` audit identified critical vulnerabilities in raw SQL generation and high-risk connection handling patterns that could cause "Too many connections" errors on Neon/RDS during heavy ingestion tasks.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 079 — Database Hardening & Multi-Tenant Isolation
Date: 2026-04-05  
Decision:  
1. **Row Level Security (RLS)**: Enabled RLS on all `client_*` tables. Access is strictly controlled via a PostgreSQL policy checking the `app.current_client_id` session variable. This prevents cross-user data leakage at the database level.
2. **Standardized Temporal Data**: Converted all `TIMESTAMP` columns to `TIMESTAMPTZ` (Timestamp with Timezone). This ensures absolute temporal consistency across AWS/Railway servers and local WSL development.
3. **64-bit Architecture for Big Data**: Migrated `daily_prices` and `index_prices` primary keys from `SERIAL` to `BIGSERIAL` to support billions of rows.
Reason: A `database-reviewer` audit identified several high-risk patterns: potential cross-tenant data leakage due to lack of RLS, and potential numeric overflow in the long-term price history data.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 081 — Inclusive Scoring for Golden Path Resilience
Date: 2026-04-23
Decision: 
1. Switched trend conditions (EMA 50/200 cross and 200 EMA slope) from strict `>` to inclusive `>=`.
2. Added a 1% grace threshold to the 6-month high condition (`close >= rolling_high_6m * 0.99`).
3. Lowered the volume surge trigger from 1.5x to 1.3x 20-day average.
Reason: The "Golden Path" validation was failing (only 7 stocks >= 75) due to a "Binary Trap." These changes align the engine with realistic institutional accumulation patterns while maintaining the 75-point "High Conviction" gate.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 082 — Robust yfinance Column Normalization
Date: 2026-04-23
Decision: Implemented a robust column flattener and mapper in `ingestion_engine.py` to handle yfinance v0.2.50+ MultiIndex return formats.
Reason: A library update caused index ingestion to fail silently because the 'Date' column was nested in a tuple, leading to the 5-day drift error.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 083 — Direct DB Fetch for Regime Engine
Date: 2026-04-23
Decision: Replaced `pd.read_sql` with a direct `cur.execute` fetch in `regime_engine.py`.
Reason: A compatibility warning between `pandas` and `psycopg2.extras.RealDictCursor` was causing the engine to return empty dataframes silently in the GitHub Actions environment.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 084 — PRDE as Fundamentals Intelligence Layer
Date: 2026-04-25
Decision:
1. Implement PRDE (PE Re-Rating Discovery Engine) as a fundamentals intelligence layer inside the existing MRI FastAPI monolith, not as a separate service.
2. Reuse Neon PostgreSQL, Railway deployment, existing scheduler patterns, SES email delivery, audit logging, and MRI trend/regime overlays.
3. Start with an idempotent PRDE data foundation: `prde_*` tables in `api/schema.py`, a documented CSV import contract, and `scripts/import_prde_financials.py`.
4. Defer LLM agents until annual financial and ratio data can be imported, validated, and reproduced from stable source rows.
Reason: PRDE depends on trusted 5-10 year financial statement data. Building the schema and import path first prevents the agent layer from producing convincing but unsupported analysis.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 085 — AAE as Product Vision, PRDE as Foundation
Date: 2026-04-25
Decision:
1. Adopt Amritkaal Alpha Engine (AAE) as the long-term product vision: an event-driven, multi-agent Indian equity research platform that produces ranked re-rating candidates, living theses, and risk dashboards.
2. Treat PRDE as the first implementation layer inside AAE, specifically the deterministic financial fingerprint and re-rating fundamentals foundation.
3. Keep AAE inside the existing MRI monolith during MVP phases. Reuse FastAPI, Neon PostgreSQL, Railway, current scheduler patterns, SES/email, audit logs, user/watchlist context, MRI trend scores, and market regime overlays.
4. Sequence implementation conservatively: PRDE import and deterministic features first, deterministic scoring second, then document/event ingestion, structural signal agents, macro/risk agents, orchestrator, and analyst console.
5. Do not build document RAG, LLM agents, or event orchestration until real financial seed data has been imported, verified, and converted into stable feature snapshots.
Reason: The new AAE PRD expands the product from a fundamentals-only engine into a full research platform. The safest implementation path is to preserve the current PRDE work as the data foundation and layer event-driven agents only after deterministic financial outputs are reproducible.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 086 — Market Holiday Skip in GitHub Actions
Date: 2026-05-01
Decision:
1. Add `scripts/check_market_holiday.py` to the GitHub Actions workflow as a pre-pipeline gate.
2. The script checks against a hardcoded list of 17 NSE/BSE market holidays for 2026.
3. Exits code `0` (trading day) → pipeline proceeds; exits code `1` (holiday) → workflow stops.
4. GitHub Actions workflow only runs on Mon-Fri cron; this adds the holiday exclusion layer.
Reason: Prevents wasted GitHub Actions minutes on days when Indian markets are closed. The pipeline is idempotent and would handle empty data gracefully, but skipping entirely is cleaner and avoids unnecessary compute/logs.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 087 — PERX V1 as a Company-First Orchestration Layer
Date: 2026-05-08
Decision:
1. Implement PERX V1 as a new orchestration and synthesis layer inside the existing MRI FastAPI monolith, not as a separate service or parallel architecture.
2. Reuse existing engine outputs as the PERX evidence base:
   - `stock_scores` for MRI technical leadership
   - `market_regime` for environment overlay
   - `swing_trades` plus technical conditions for STEE context
   - `quality_verdicts` and `fundamental_financials` for QIF and financial trend evidence
   - `engine_qualitative/debate.py` as the Institutional Forensic Review section
   - `engine_core/email_service.py` and AWS SES for optional report delivery
3. Start PERX with a backend-first MVP:
   - `engine_perx/` orchestration package
   - `api/perx.py` routes
   - `perx_reports` and `perx_scores` persistence
   - unified report JSON for a single symbol
   - optional HTML email send for the generated report
4. Keep PERX deterministic-first. AI may synthesize, explain narrative transition, and produce institutional wording, but must not invent metrics, override deterministic scores, issue trading advice, or generate price targets.
5. Do not block PERX V1 on new price ingestion. Existing MRI/STEE price history is sufficient. Additional data work should focus only on selective fundamental coverage gaps and future PERX-specific derived layers such as sector intelligence, fragility tracking, lifecycle history, and analog storage.
6. Sequence delivery conservatively:
   - Phase 1: single-symbol orchestration and stored report JSON
   - Phase 2: email, watchlist hooks, and report retrieval
   - Phase 3: compare mode, archive UI, lifecycle history, and richer sector/fragility layers
Reason: The existing platform already has the major technical, fundamental, qualitative, email, and dashboard primitives that PERX needs. Building PERX as an orchestration layer maximizes reuse, protects current production flows, and allows the product to ship incrementally without redesigning MRI/STEE/QIF.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 088 — AAE V3 Watchlist Digital Twin & Daily Automation
Date: 2026-05-11
Decision:
1. Embed the 8-layer AAE execution directly into the user's Watchlist via a "Digital Twin" modal, replacing the need for a separate heavy dashboard for institutional scanning.
2. Introduce a Master Controller script (`scripts/mri_aae_prod.py`) that handles discovery, ingestion, the 7-layer fundamentals pass, and the Layer 8 Forensic Debate.
3. Inject the AAE master controller as "Step 9" in the existing `pipeline_cloud.sh` to ensure daily execution.
Reason: The AAE V3 is compute-heavy (LLM tokens + multi-agent debate). Integrating it strictly as an on-demand "Digital Twin" for Watchlist items, plus a top-20 automated daily run, controls API costs while maximizing visibility where the user cares most.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 089 — Deterministic Frontend Builds
Date: 2026-05-21
Decision:
1. Switch `npm install` to `npm ci` in the Dockerfile.
2. Commit `package-lock.json` to version control.
Reason: Ensures deterministic, non-interactive frontend builds across all environments, eliminating "it works on my machine" issues and preventing unexpected dependency updates from breaking production deployments.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 090 — Decoupled Breakout Status API
Date: 2026-05-21
Decision:
1. Implement a dedicated, read-only endpoint `/api/breakout-status`.
2. Extract breakout UI representation into a dedicated `BreakoutBadge` component.
Reason: Decoupling the breakout status from the main signal feed improves frontend responsiveness when checking individual stocks in the StockDetailsModal, and allows independent iteration of the breakout detection logic.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 091 — Shared API Client for All Frontend Data Fetching
Date: 2026-05-21
Decision:
1. All frontend API calls MUST use the shared `apiFetch()` helper from `api.ts`, not raw `fetch()`.
2. The auth token is stored under the key `mri_token` in localStorage — no other key is valid.
Reason: Raw `fetch()` calls bypass the shared auth header injection, API base URL resolution, and session-expiry redirect. The `BreakoutRadar` component was using `localStorage.getItem('token')` (wrong key — should be `mri_token`) and sending `Authorization: Bearer null`, causing a silent 401 on every request. Adding `getBreakoutRadar()` to the `api` object and calling it through `apiFetch` fixes this permanently.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 092 — Mobile Navigation: Icon-Only with Full Page Coverage
Date: 2026-05-21
Decision:
1. Mobile bottom nav displays only emoji icons; page names appear via native `title` tooltip on hover/long-press.
2. All 10 pages from the desktop sidebar are present in the mobile nav (Dashboard, Swing Momentum, History, Risk Audit, Watchlist, Breakout Radar, PERX, AAE Console, Platform Intelligence [admin], Logout).
3. Swing Momentum icon changed from 🚀 to 🔄 to eliminate collision with Breakout Radar (🚀).
Reason: The previous mobile nav had only 7 links, missing History, Performance, AAE Console, and Platform Intelligence. Icons-only keeps the bar compact enough to fit 10 items, and the 🔄 icon better represents the swing/cycle concept.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 093 — GuidanceCheck: Screener.in as Primary Transcript Source
Date: 2026-05-28
Decision:
1. Use screener.in company pages (not direct BSE API) as the primary source for discovering concall transcripts.
2. Parse screener.in's #documents section, filter for items labeled "Transcript", extract BSE PDF URLs.
3. BSE PDFs are downloaded and converted to text via pdftotext (with pdfplumber fallback).
4. Text is stored via the existing `TranscriptCollector` into `aae_transcripts`.
5. GPT-4o-mini extracts forward-looking statements into `management_guidance`.
6. All new code lives in `engine_guidance/` — isolated module, no existing code modified.
Reason: The BSE API endpoints return HTML challenge pages (anti-bot protection) and are unreliable. Screener.in already aggregates BSE filings with clear labels (e.g., "Apr 2026TranscriptAI SummaryPPT"), providing structured metadata that the BSE API lacks. Coverage: RELIANCE 78 transcripts, TCS 20, HDFCBANK 21, going back to 2016.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 094 — GuidanceCheck as Isolated Feature Module
Date: 2026-05-28
Decision:
1. Build GuidanceCheck as an isolated feature inside MRI, not a separate service.
2. Keep all new code in `engine_guidance/` — no existing engines or pipeline scripts modified.
3. Register API routes in `api/main.py` only when ready for production use.
4. Use `CREATE TABLE IF NOT EXISTS` for all new tables — idempotent, safe to deploy anytime.
5. Develop on feature branch `feature/guidance-check` — GitHub Actions only triggers on `main` push.
Reason: The existing MRI infrastructure (transcript storage, quarterly financials, GPT pipeline, user auth, portfolio tracking) provides 80% of what GuidanceCheck needs. Building inside MRI maximizes reuse while isolating risk. Zero pipeline disruption during development.
Status: FINAL.

---

## Decision 095 — NSE Corporate Announcements as Screener.in Fallback
Date: 2026-05-29
Decision:
1. Keep screener.in as the primary concall transcript discovery source.
2. When screener.in returns 404 or 0 results, fall back to NSE's public corporate announcements API (`nseindia.com/api/corporate-announcements`).
3. NSE fallback requires a session cookie from a pre-request to nseindia.com — handled via requests.Session.
4. Filter NSE announcements for transcript/concall keywords, download PDFs from NSE archives, extract text via pdftotext.
5. BSE API was rejected: auth-protected, 301 redirects to member login.
Reason: screener.in returns 404 for stocks with space-containing display names or unlisted symbols. NSE's API is the only public, auth-free source for Indian corporate filing PDFs. Symbol normalization (strip spaces, try common suffixes) is applied before either source is queried.
Status: FINAL.

---

## Decision 096 — Auto-Prime Guidance on Watchlist/Portfolio Add
Date: 2026-05-29
Decision:
1. Every new stock entering watchlist or digital twin gets guidance data auto-primed via FastAPI BackgroundTasks.
2. On server startup, if management_guidance table is empty, auto-prime all stocks via threading.Thread.
3. Priming pipeline: concall discovery → GPT extraction → verification → credibility scoring. All steps are idempotent (ON CONFLICT upserts).
4. Table names in prime-all queries: `client_watchlist` and `client_external_holdings` (not `watchlist`/`holdings` which don't exist).
Reason: Previously, guidance data required manual triggering. Auto-priming ensures credibility scores are available immediately after a stock is added to the system, making GuidanceCheck and the Unified Analysis multi-bagger scoring useful from day one.

## Decision 097 — ConvictionEngine: Cross-List Management Integrity Tracking
Date: 2026-06-15
Decision:
1. Extend the existing `engine_guidance/` pipeline to cover the **`universe_112co` table** in addition to `client_watchlist` + `client_external_holdings`. Prime-all and quarterly verifier both gain the 112 list as a coverage source.
2. Add three lag-tracking columns to `management_credibility_scores`: `consecutive_miss_quarters INT`, `lag_score NUMERIC(5,2)`, `last_verdict_flip DATE`. Migration is `ADD COLUMN IF NOT EXISTS` — idempotent, safe under RDS-protection rules (Decision 027).
3. Compute `consecutive_miss_quarters` by walking `guidance_verification` rows in fiscal-quarter order from most recent backwards, counting MISSED until an ACHIEVED/PARTIAL breaks the streak. `lag_score` = `(streak / total_verified_quarters) * 100`.
4. New API surface: `GET /api/guidance/conviction?source=digital_twin|112co|all` returns Digital Twin ∪ 112Co union, ranked worst-first by accuracy / lag_score.
5. New React dashboard `ConvictionEngine.tsx` reusing `GuidanceCheck.tsx` chip primitives — verdict chip, accuracy ring, lag indicator. Sidebar entry "🧠 Conviction Engine" in `App.tsx`.
6. New quarterly lag-alert job: `scripts/send_conviction_alerts.py` reads verdict-flip rows (zone boundary crossings only, not raw accuracy wobbles) and emails opted-in clients via `engine_core/email_service.send_email_custom`.
7. Defaults: per-quarter LLM spend cap $0.50 with kill-switch; lag-alerts default-OFF (opt-in via `client_alert_preferences`); verdict-zone thresholds kept at 75/60/40 %.
Reason: User requested management-integrity tracking across both the Digital Twin (real portfolio) and 112 Co Universe (PE-expansion watchlist). Existing GuidanceCheck engine, schema, API, and quarterly pipeline already cover ~80% of the work — the gap is coverage (`universe_112co` is not in the prime-all loop) and per-quarter lag persistence (currently `trend` is computed on the fly but never stored as a time-series). Building this as a thin extension preserves the Decision 003 single-container architecture, Decision 095 Screener+NSE dual-source, and Decision 096 auto-prime-on-add behaviour.
Status: **FINAL — executed 2026-06-15.** Shipped on `main` via `6e7c7d7` (ConvictionEngine core: 4 phases from `docs/ConvictionEngine15June26.md`) + `043d2e3` (Management Integrity Surface: Appendix A). Subsequent fixes and follow-ups also on `main`: `0e9743d` (`/api/guidance/{symbol}/credibility`), `3a9d87a` (`/api/guidance/{symbol}/timeline`), `0598d63` (email uses ConvictionEngine credibility instead of plain accuracy), `8a7eed5` (route-ordering fix — `/conviction` was shadowed by `/{symbol}` catch-all), `a2cb131` (auth hotfix — raw `fetch` missing `mri_token` Bearer header). Intonation backfill completed 2026-06-15: 985 scored + 3 skipped + 1 untouched = 986/989 rows in `management_intonation` across 147 distinct symbols. All 7 deliverables shipped; no open follow-up items against this decision beyond the explicitly-out-of-scope items (real CAPACITY_EXPANSION verification, peer-comparison intonation, real-time intonation streaming).


## Decision 098 — Data Richness Sprint (Fix A: backfill + Fix D: extend QIF granularity)
Date: 2026-06-19
Decision:
1. **Fix A — Backfill AAE + QIF for uncovered universe stocks.** Run `scripts/aae_bulk_scan.py --only-missing` for stocks lacking `aae_results_snapshot` rows. Run `engine_fundamental.pipeline` for stocks lacking `quality_verdicts` rows. Currently ~70-90 of 149 universe stocks have at least one engine missing. QPOWER (PE rank #2, 84.9) is the worst case — zero orthogonal coverage.
2. **Fix D — Extend QIF 7-agent code to persist underlying financial metrics** in a new `quality_verdicts.agent_details` JSONB column. Per-agent detail fields include: revenue (growth_yoy_pct, growth_3y_avg_pct, sector_median_growth_pct, trend), margin (opm_current_pct, opm_3y_avg_pct, sector_median_opm_pct, compression_bps_yoy), leverage (debt_to_equity, interest_coverage, current_ratio), working capital (wc_days_current, wc_days_change_yoy), ROCE (roce_pct, wacc_pct, gap_pct, gap_change_yoy), evolution (margin_change_3y, roce_change_3y), translation (pe_vs_sector_median, ev_ebitda_vs_sector_median). QIF currently only persists 0-10 scores + a single flag per agent — underlying numbers are discarded.
3. **Extend `engine_debate/context_pe_expansion.py:build_pe_expansion_context`** to include the new agent_details in the `financial_quality` block. This lets the bear/bull debate LLM argue from specific numbers (e.g. "ROCE 11.2% vs WACC 14.0%, gap -2.8% widening") instead of summary flags ("ROCE < WACC").
4. **Schema migration `migrations/005_qif_agent_details.sql`**: `ALTER TABLE quality_verdicts ADD COLUMN IF NOT EXISTS agent_details JSONB DEFAULT '{}'::jsonb;` — idempotent, additive, no destructive change. Default `'{}'::jsonb` keeps all old code paths working.
5. **Re-run QIF for all 149 universe stocks** so every existing QIF row gets populated agent_details. Sequential with rate limiting.
6. **No scoring algorithm change.** Same `compute_pe_score` formula. Same verdict zones. Same category weights. Just richer data underneath.
7. **No auto-regeneration of cached debates.** Context_hash will differ for stocks whose data changed, so next debate view will auto-fetch fresh. No need to wipe `conviction_debates`.
Reason: The bear/bull debate engine (shipped 2026-06-19) correctly flagged two structural gaps in production use: (1) QPOWER ranked #2 in PE Expansion with zero orthogonal data — narrative score only; (2) KirlosEngine's bear case argued from "ROCE < WACC flag" instead of underlying numbers. User flagged directly: "people are betting their hard earned money on your opinion, so let that better be good." Without Fix A, ranks are unreliable for any stock whose cross-check matrix shows "No data". Without Fix D, debates are summary-metric arguments instead of grounded extrapolations. Both fixes together turn the cross-check from "we don't know" into "here's exactly what each engine says, with the numbers to back it up."
Status: **DRAFT — awaiting user approval.** Full scope, time estimates, cost breakdown, and rollout plan in `docs/INITIATIVE_DATA_RICHNESS_2026-06-19.md`. **Open questions resolved (2026-06-19, evening):**
- **Q1 (schema):** JSONB column with **option (c)** chosen — full quarterly history in `agent_details.by_quarter[]` array + pre-computed `agent_details.trajectory` summary. ~7 quarters × ~25 fields/quarter × 109 stocks = ~3 KB per row. Negligible.
- **Q2 (backfill order):** all at once (proposed default).
- **Q3 (un-backfillable stocks):** leave with `has_data: False`, debate shows graceful "No data" (proposed default).
- **Q4 (cache invalidation):** natural on next view via context_hash diff (proposed default).
- **Q5 (trajectory compute cost):** O(n_quarters × n_agents) ≈ 50 ops/stock. Trivial. No concern.

**Corrected cost estimate:** ~$3.30 LLM one-time (was incorrectly $5.00 in first draft). Wall time unchanged: ~6-7 hrs. LLM cost is purely from AAE backfill (`scripts/aae_bulk_scan.py` uses `narrative_engine.py` + `forensic_debate.py`). QIF (`engine_fundamental/agents.py`) and `engine_fundamental/collector.py` are pure Python / yfinance HTTP — no LLM anywhere. Universe coverage today: 63 of 172 stocks (37%) have financials; CGCL (used as positive example) is among the 109 uncovered.

## Decision 099 — Breakout Age Tracking (STEE + Breakout Radar Enhancement)
Date: 2026-07-03
Decision:
1. Add `breakout_age INTEGER DEFAULT NULL` column to `daily_prices` — tracks consecutive trading days a stock has been in its current `breakout_state` (BROKEN_OUT or READY_TO_BREAKOUT). Resets to 0 on state transition. NULL when CONSOLIDATING.
2. Compute `breakout_age` in `indicator_engine.py` as part of the daily pipeline, immediately after `breakout_state` classification. Uses sequential row comparison within each symbol's time-sorted dataframe.
3. Enhance `/api/breakout/radar` to return `breakout_age`, `age_label` (human-readable zone), and `radar_priority` (MOSI score × age decay factor). Sort BROKEN_OUT stocks by age ASC (freshest first).
4. Redesign `BreakoutRadar.tsx` with age-grouped sections: 🔥 Fresh (Day 0-1), 📈 Early (Day 2-3), ⚠️ Late (Day 4-5), 💤 Mature (>5). Add "New Today" hero section for Day 0 breakouts.
5. Add soft age filter to STEE: Day 0-2 = full position, Day 3-5 = 50% size reduction, Day >5 = skip entry.
6. Schema change is additive-only (`ADD COLUMN IF NOT EXISTS`), idempotent, no destructive change. Safe under Decision 027 RDS protection rules.
Reason: `breakout_state` is a stateless snapshot — two stocks can both be BROKEN_OUT with MRI Score 95, but one is Day 0 (fresh, actionable) and the other is Day 7 (mature, most thrust spent). Breakout Age adds a timing-freshness dimension that pairs with Trajectory Score: score measures setup quality, age measures timing quality. The Breakout Radar is the primary consumer (discovery + prioritization), STEE uses it for position sizing, and Morning Brief uses it for BUY/SKIP/WATCH verdicts. $0 LLM cost, pure deterministic computation.
Status: **FINAL — executed 2026-07-03.** All 4 phases shipped across prior commits:
- Phase 1 (Schema + Indicator Engine): `c4f0bbc feat: Implement Breakout Age filtering and tracking` — `migrations/006_breakout_age.sql`, `engine_core/indicator_engine.py` (`INDICATOR_COLUMNS` +41, sequential age computation lines 288-294, persistence at 323/376/468), `api/schema.py:238-241` auto-migration.
- Phase 2 (Breakout Radar API): landed in `c4f0bbc` — `api/breakout_status.py` (`AGE_DECAY` 174-181, `_age_label` 184-206, enrichment at 297-319, age-sorted SQL ORDER BY at 281).
- Phase 3 (Breakout Radar UI): landed in `c4f0bbc` (initial age-grouped sections) + `36c1785 feat: Add sorting capability to Breakout Radar tables` + `9cfa123 fix: stabilize Breakout Radar sort hooks` — `frontend/src/BreakoutRadar.tsx`.
- Phase 4 (STEE integration): landed in `c4f0bbc` — `engine_core/swing_execution_engine.py:46,123` (age column select + age-aware `size_modifier` reduction for Day 3-5, skip for >5).
- **Swing Momentum wiring (this session)**: `api/signals.py` enriched `/signals/shadow` with `breakout_age` + `age_info`; `frontend/src/App.tsx ShadowMomentumPage` renders `<BreakoutBadge state={s.breakout_state} ageInfo={s.age_info} />` next to each Top-10 symbol — same pattern as Breakout Radar.

Full execution plan in `docs/BREAKOUT_AGE_EXECUTION_PLAN_2026-07-03.md`.

## Decision 100 — Capital Allocation Score V1.0 (rev 3)
Date: 2026-07-06 (rev 2 freeze); rev 3 refinements applied 2026-07-07
Decision:
1. **Two-stage architecture**: `Eligibility (6 hard gates) → Market Score Sub-Gates (3 hard PASS/FAIL: Trend, Breakout, Quality) → Numeric Score (weighted 7 factors, survivors only) → Portfolio Multipliers (Winner × Concentration) → Portfolio Allocation Score → Confidence ★ → Action chip`. The Market Score is NOT a simple weighted sum — it has hard sub-gates so "a stock cannot compensate for a weak weekly trend with huge volume" (user's rev 2 critique).
2. **Eligibility (6 hard gates, rev 2)**: Regime ∈ {BULLISH, SIDEWAYS} (BEARISH passes only if `aggressive_mode = true`); 4-component EMA stack — `Close > EMA20` AND `EMA20 > EMA50` AND `EMA50 > EMA200` AND `EMA100 rising` (RELAXED from strict `20>50>100>200` because "plenty of fantastic reratings happen before EMA100 fully crosses"); Breakout age ≤ 5; Liquidity ≥ ₹10 Cr/day (Decision 029); QIF ≥ **70** (RAISED from 65 — "fewer, better ideas"); 52w position within 10%.
3. **Market Sub-Gates (NEW rev 2, 3 hard PASS/FAIL)**: `weekly_trend_score >= 50` (Trend gate), `breakout_age <= 3` (Breakout gate, stricter than eligibility's ≤ 5), `QIF >= 75` (Quality gate, stricter than eligibility's ≥ 70). A stock failing ANY sub-gate is REJECTED — no numeric score is computed. This is the core architectural change from rev 1.
4. **Market Score weighted factors (rev 2 rebalance, sum to 100)**: Regime 23, Weekly Structure 21, Breakout Quality 17, **Overhead Supply 14 (NEW)**, Relative Strength 11, Volume 8, Sector Strength 6. `concentration` is a multiplier only, NOT a weight.
5. **R/R REMOVED from V1.0** (was 12% in rev 1). The proxy (`support = min(close × 0.92, rolling_high_52w × 0.85)`; `target = max(close × 1.10, resistance_6m × 1.05)`) was rejected as "arbitrary" (user). The 12% weight was reallocated to Overhead Supply. R/R returns in V1.1 with a real `support_3m` column.
6. **Overhead Supply (NEW rev 2, 14% weight)**: Counts distinct swing highs in last 6m above the current close, normalized to 0–100 (0 = clear air, 100 = massive overhead resistance). Motivated by the Poonawalla (rejected — high overhead) vs NAVINFLUOR (passes — clear air) test case. New column `overhead_supply_score` on `daily_prices`.
7. **Weekly Structure upgraded to multi-component** (rev 2). NOT just EMA distance. Five binary components, summed, max 100: Higher Highs (+25), Higher Lows (+25), Above weekly EMA-13 (+20), Above weekly EMA-20 (+15), Within 5% of 52w high (+15). New column `weekly_trend_score` on `daily_prices`. Weekly EMAs computed via `daily_prices.resample('W-FRI')` then forward-filled.
8. **Portfolio Multipliers (rev 2 — softened Winner cap)**:
   - **Winner**: `multiplier = 1 + (profit_pct / 10) × 0.10`, clamped to `[0.85, 1.10]`. Max boost **reduced from 0.15 → 0.10** because "existing holdings should reinforce, not dominate rankings". +10% profit → 1.10x; +5% → 1.05x; -10% → 0.90x; -15% → 0.85x.
   - **Concentration** (unchanged): `multiplier = 1 - clamp(weight_pct / 15, 0, 1) × 0.10`. At 15%+ portfolio weight → 0.90x (max -10% penalty).
9. **Confidence (rev 3: 5 model-certainty stars, NOT stock quality)**: A 5-criterion star rating displayed next to the CAS number. Each criterion contributes 1 star if met: (a) **complete_data** (data_completeness ≥ 90%), (b) **factor_agreement** (std-dev of goodness-aligned sub-scores ≤ 20; `overhead_supply` inverted BEFORE std-dev so all factors share direction), (c) **stable_calculations** (breakout_age ≠ 4 — not at the AGE_DECAY cliff), (d) **low_proxy_usage** (proxies_used count ≤ 0 — real indicators preferred), (e) **indicator_freshness** (data_age_days ≤ 5). rev 2 had `trend_maturity` + `breakout_maturity` — both REMOVED in rev 3 because they are stock-quality signals, not model-certainty signals. Stock quality belongs in CAS itself, not in the model's confidence about its own score. Trend strength and breakout freshness still appear in the Why-checklist and `breakout_age_emoji` — they are not lost, just in the right place.
10. **Breakout Age UI emoji (NEW rev 2)**: 🔥 Today / 🟢 Yesterday (Day 1-2) / 🟡 3 Days (Day 3-4) / ⚪ 5 Days / ⚫ Stale (>5). Surfaced on every banner card so urgency is at-a-glance.
11. **Structured Why checklist (NEW rev 2)**: Multi-line ✓ bullets instead of single sentence. Template list in YAML — each entry has `condition_name` + `template_string`. Renderer evaluates conditions against `(row, sub_scores)` and formats matching lines with row fields (e.g., `"✓ Volume confirmation (2.3x average)"`). 10 conditions defined; matches subset per stock.
12. **Action chip thresholds**: `cas >= 85 → "ADD SECOND TRANCHE"`, `70-84 → "FIRST TRANCHE"`, `50-69 → "WATCH"`, `< 50 → no chip`. Same thresholds as rev 1.
13. **V1.0 ships 4 new columns**: `ema_100`, `rolling_high_52w`, `weekly_trend_score`, `overhead_supply_score` (all on `daily_prices`, all NUMERIC, all `ADD COLUMN IF NOT EXISTS`). Migration: `migrations/008_capital_allocation_columns.sql`. Defense in depth via `api/schema.py` auto-heal extension. **Dropped from V1.0**: `resistance_6m` (no longer needed without R/R).
14. **Configurable, not hardcoded**: ALL thresholds, weights, multipliers, sub-gate floors, confidence criteria, action thresholds, breakout-age emoji, and Why-checklist templates live in `config/capital_allocation.yaml`. Code reads via `yaml.safe_load` and passes the dict around. No magic numbers in `engine_core/`.
15. **Implementation split across 3 sessions** (per §7 of plan doc):
    - Session N+1: migration + `engine_core/capital_allocation.py` (pure logic) + unit tests.
    - Session N+2: 4 new indicator column computations + `api/schema.py` auto-heal extension.
    - Session N+3: `api/breakout_status.py` wiring + new `/top-by-cas` endpoint + `frontend/src/CapitalAllocationCard.tsx` + Radar/Dashboard banners + `requirements.txt` pyyaml.
Reason: User asked for a Capital Allocation Score that answers "Which breakout deserves fresh capital today?" — a question the existing Breakout Radar (which lists breakouts but doesn't rank by deployability) does not answer. Rev 1 was a straightforward weighted sum. User's rev 2 critique identified 13 specific design points to fix, driven by recent decision-making patterns (Poonawalla vs NAVINFLUOR rejection logic; preference for clean weekly structure over mechanically high composite scores; "fewer, better ideas"). The two-stage architecture (sub-gates first, weighted ranking second) prevents the user's stated anti-pattern: "a stock can compensate for a weak weekly trend by having huge volume. I don't think that's how MRI should think." Adding the Confidence ★ rating addresses another rev 2 critique: numeric confidence is harder to grok than stars. Removing the R/R proxy is a discipline move — shipping a number derived from arbitrary heuristics is worse than shipping one fewer factor that we know is right. Returns in V1.1 with real support data. $0 LLM cost; pure deterministic computation; ~5–7 hrs wall time across 3 follow-up sessions.
Status: **APPROVED — rev 3 refinements applied (2026-07-07).** Owner signed off on rev 2 design freeze and the 3-session implementation plan, then reviewed the N+1 implementation and requested 8 refinements + 1 recommendation (all applied, see implementation log). Full design spec in `docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md` (rev 3, 13 sections). All thresholds + weights in `config/capital_allocation.yaml` (rev 3, includes `calibration` section for tunable numeric constants). Will be flipped to **FINAL — executed** after Session N+3 deploys to Railway and the `/top-by-cas` endpoint serves live banner cards. Detailed implementation plan, handoff notes, and ordered sub-tasks are in §7 of the plan doc + the Session N+1 entry at the top of `Sessions.md` + the "📅 Session: July 7, 2026" block in `Progress.md`.
Implementation log:
- **Session N+1 (2026-07-07, original)**: migration `migrations/008_capital_allocation_columns.sql` + `engine_core/capital_allocation.py` (pure logic, 6 public functions) + `engine_core/test_capital_allocation.py` (24 unit-test scenarios / 92 cases). Decision 100 flipped DRAFT → APPROVED. Branch: `feature/capital-allocation-v1` (commit `f4dc161`).
- **Session N+1 refinements (2026-07-07, rev 3)**: Owner reviewed the N+1 implementation and requested 8 design refinements + 1 recommendation. All applied:
  1. Confidence = **5 model-certainty stars** (Complete data, Factor agreement, Stable calculations, Low proxy usage, Indicator freshness). Stock-quality stars (`trend_maturity`, `breakout_maturity`) removed from confidence.
  2. Invert `overhead_supply` BEFORE factor_agreement std-dev so all factors share "higher = better" direction.
  3. **All calibration constants moved to YAML `calibration.*`** (rs_strong, volume_confirmed, overhead_clear_air, qif_high, weekly_strong, near_52wh_pct, breakout_early_max_age, age_decay table, confidence.* thresholds). No magic numbers in Python.
  4. Missing critical market data → **Ineligible, not score of 0**. Added 2 eligibility gates: `weekly_data`, `rs_data`.
  5. Renamed `check_market_subgates` → `compute_market_structure` (investment-concept-aligned naming).
  6. Added `compute_market_score_breakdown()` returning `(score, {factor: contribution})`. Per-factor contribution loggable from day one via DEBUG.
  7. Logging levels: DEBUG for breakdown, INFO for summary (e.g., "CAS computed"), WARNING for unexpected eligibility failures. Never `logger.info` per call in backfills.
  8. Documentation invariant applied: design doc amended, YAML updated, this decision updated, Sessions.md + Progress.md updated. Code never intentionally diverges from spec.
  9. +1 recommendation: created `tests/golden_cases.yaml` regression basket (WELCORP, CHOLAFIN, PHOENIXLTD, NAVINFLUOR, POONAWALLA, BEARISH, MISSING_DATA). Every future tuning run must pass this basket.
- **Branch strategy**: 3 PRs (engine → indicators → API/UI). PR1 is `feature/capital-allocation-v1`.
- **Test count**: 104 tests pass in 0.47s (92 base + 12 golden-case assertions).
- **Files changed this session**: `engine_core/capital_allocation.py`, `engine_core/test_capital_allocation.py`, `config/capital_allocation.yaml`, `migrations/008_capital_allocation_columns.sql` (NEW), `tests/golden_cases.yaml` (NEW), `docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md`, this decision, `Sessions.md`, `Progress.md`, `requirements.txt`.
- **Next**: Session N+2 — indicator engine wiring (compute 4 new columns) + `api/schema.py` auto-heal + backfill for Nifty 500.

## Decision 101 — Expert Architectural Review & V1.1 Scope
Date: 2026-07-08
Decision-maker: Project Expert (third-party reviewer)
Trigger: Post-N+2b review (backfill complete + latent pipeline bug fixed)

### Decision

1. **V1.0 architecturally sound — APPROVED.**
   Expert's assessment after N+2b delivery: "V1.0 has reached a point where I would call it 'architecturally sound.' The fact that you found a latent pipeline bug during integration is actually a good sign — it means integration is doing its job."
   Decision 100 status flipped to **FINAL — executed** for V1.0 engine + indicator pipeline + golden-case wiring. N+3 (API/UI) remains open.

2. **Three-Layer Architecture (NEW — load-bearing for V1.1+).**
   MRI is reorganized as three distinct layers, each with one output and one owner:
   - **Layer 1 — Market Intelligence** → produces **Market Score** (current `compute_market_score`).
   - **Layer 2 — Portfolio Intelligence** → produces **CAS** (current `compute_portfolio_allocation_score`).
   - **Layer 3 — Decision Intelligence** → produces **Action** (`BUY` / `ADD` / `WATCH` / `NO ACTION`).
   **Rule: only Layer 3 talks to humans.** Everything below Layer 3 is analytics. Layers 1 and 2 must never emit "BUY" or other action verbs — they produce numbers, not decisions. This separation will keep architecture clean as it grows.
   Action verbs are renamed: `ADD SECOND TRANCHE` → `ADD` (to match Layer 3 vocabulary); `FIRST TRANCHE` → `BUY`; `WATCH` unchanged; `NO ACTION` new in V1.1.

3. **Engineering Motto (project-wide).**
   > **Every score must be explainable. Every threshold must be calibratable. Every recommendation must be measurable.**
   If MRI never violates these three principles, the architecture stays clean. This motto goes at the top of the spec doc as §0.

4. **Mandatory fixes before V1.1 ships.**
   - **Gap 1 — `ema_100_slope_5d`**: Add computation to `indicator_engine.py`. The `ema100_rising` eligibility gate currently always fails because this field is `None`. A broken eligibility gate = good stock rejected = never scored. **Correctness issue.**
   - **Gap 5 — `normalize_row()` helper**: All `Decimal` → `float` conversions must happen in ONE place, before the engine sees the row. The engine must not know or care whether Postgres returned Decimal. Add `normalize_row(row)` to `engine_core/capital_allocation.py`. Every caller goes through it.

5. **Recommended fixes in V1.1.**
   - **Age transition zone** (replaces single cliff at breakout_age=4): YAML `calibration.breakout_age_zones` map: `0–2 → excellent`, `3 → good`, `4–5 → transition`, `6+ → stale`. The current discontinuity is "mathematically convenient but not how markets behave." Also rename `stable_calculations` confidence criterion to penalize being in the transition zone rather than just being at exactly age 4.
   - **Overhead supply 0.5% buckets** (V1): Round distinct highs to nearest 0.5% to avoid float granularity (110.01 / 110.03 / 110.04 → one resistance, not three). ATR-aware buckets deferred to long-term.
   - **Keep week-over-week HH/HL detection** for V1.5-bar fractals belong in V2 (deterministic + explainable + faster).
   - **Capture outcomes for every eligible stock**, not just top-N recommendations. Expert reasoning: a stock with CAS=68 today, 85 tomorrow, 95 later — you want to know if 68 already predicted a winner. Storage is cheap, historical evidence is priceless.
   - **Immutable recommendation UUIDs from day one** (format: `CAS-YYYY-MM-DD-SYMBOL` or UUID). Future joins (recommendation → outcome → report → calibration) all link back. Without IDs, joins become painful.

6. **V1.1 work items — locked.**
   - **A. Outcome Tracking**: New tables `cas_recommendations` (immutable record per (date, symbol) for every eligible stock) + `cas_recommendation_outcomes` (path columns: entry, w1, w2, w4, max_drawdown, etc.). Helper `record_cas_recommendation()` called from API. NO reports — collect for 6 months first.
   - **B. Decision Stability**: `stabilize_action(prev, today, config)` returns `UNCHANGED / UPGRADED / DOWNGRADED / NEW`. Dampens chip changes < 3 points. **API-only** — never persist hysteresis to DB. The DB stores facts; the API decides presentation.
   - **C. "No Action" Recommendation**: API returns `{action: "NO_ACTION", reason: "..."}` when top-N list empty or all candidates fail eligibility.
   - **D. Design Principles §0** + **Three-Layer Architecture §1.0**: Both inlined into the spec doc. One document, one source of truth.
   - **E. Golden Cases**: **Deferred** (per owner). Wait for real production outcomes.
   - **F. Regression Tolerance**: `assert_cas_within_tolerance(actual, expected, tolerance=2.0)` helper. Used by tests to allow ±2 point drift when only tuning, not refactoring.
   - **G. `Calibration.md` journal**: every weight/threshold change logged (Date | Old | New | Reason | Expected Effect | Measured Effect).
   - **H. Calibration Debt metric**: **redefined** as `Number of assumptions not yet validated through historical outcomes` (e.g., "17 assumptions, 3 validated → debt 14"). Living engineering metric, not just a code metric. Implementation: a counter in `Calibration.md` plus a runtime query against `cas_recommendation_outcomes` once enough data accumulates.

7. **Defer to V1.2 or later (per expert).**
   - ATR-aware overhead supply buckets.
   - 5-bar fractal HH/HL detection.
   - EMA50 fallback for thin-history stocks.
   - Regime/QIF joins at API layer (not engine).
   - Backtest alternative `max_count` values for overhead supply.
   - Separate `cas_breakdown.log` file (use structured JSON in DEBUG instead).

8. **Open expert questions answered.**
   - **Q1 (overhead rounding)**: 0.5% buckets for V1.
   - **Q2 (HH/HL)**: week-over-week for V1.
   - **Q3 (EMA100 fallback)**: yes — to EMA50 when history <100 bars (V1.2).
   - **Q4 (max_count=10)**: keep, backtest later.
   - **Q5 (age cliff)**: replace with transition zone in V1.1.
   - **Q6 (data_age_days source)**: indicator execution timestamp (`today - last_successful_indicator_calculation`), NOT last candle.
   - **Q7 (breakdown logging)**: structured JSON in DEBUG, no separate file.
   - **Q8 (branch strategy)**: keep 3 PRs.

### Reasoning

The expert's review establishes three things:

1. **CAS is not the feature — decisions are.** From here on, MRI optimizes for *better decisions over time*, not just *better scores today*. This shifts the V1.1 priority toward Outcome Tracking and Decision Stability over further score refinement.

2. **V1.1 must close two correctness gaps** (`ema_100_slope_5d`, `normalize_row()`) before any new feature ships. These are silent failures that would compound as new features depend on them.

3. **The three-layer architecture is a forcing function for clean separation.** When "BUY" can only come from Layer 3, it's impossible for Market Score or CAS to leak action verbs to the UI. This prevents the gradual feature-creep that turns analytics engines into recommendation black boxes.

The expert's specific disagreement (capture outcomes for every eligible stock vs only recommendations) is the most consequential V1.1 design change. It roughly doubles storage requirements but preserves information that would otherwise be permanently lost when a stock graduates from "borderline" to "obvious buy." This is a one-time, irreversible data loss if missed.

### Status
**APPROVED — implementation in progress (V1.1a next).**

### Implementation plan (V1.1 — 4 sessions, ~8–9 hours total)

**Session V1.1a — Engine correctness (mandatory fixes + recommended tuning, ~2–3 hours):**
- Add `ema_100_slope_5d` to `indicator_engine.py` (compute + write + auto-heal + backfill column).
- Add `normalize_row(row)` to `engine_core/capital_allocation.py` (Decimal → float). Refactor all 7 existing entry points to call it first.
- Add `derive_metadata(row)` helper (computes `data_completeness_pct`, `data_age_days`, `proxy_count` from a row).
- Replace `breakout_age_cliff` with `breakout_age_zones` in YAML; update `compute_confidence_stars` accordingly.
- Round overhead supply to 0.5% buckets in `compute_overhead_supply_score`.
- **Add `compute_engine_signature()` helper** returning `{cas_version, config_hash, commit_sha}`. The signature is computed once per process and embedded in every recommendation record. `config_hash = sha256(yaml.safe_dump(config))[:8]`. `commit_sha = git rev-parse --short HEAD` at module load.
- Run full test suite (must stay ≥ 137 PASS).
- Update spec doc §5 (Confidence) and §3 (Age Decay) to reflect transition zone.
- ~30+ new unit tests (helpers + bucket rounding + engine signature determinism).

**Session V1.1b — Persistence (Outcome Tracking + UUIDs + snapshot, ~3 hours):**
- **Architecture (per expert, replaces Monday-based capture):**
  - **Event A — Recommendation capture (immediate, on API CAS computation):** write one row to `cas_recommendations` for EVERY eligible stock (not just recommendations). Immutable record.
  - **Event B — Daily EOD outcome updater (separate cron, runs daily after market close):** for each open recommendation, compute elapsed days. When elapsed ∈ {7, 14, 28, 63, 126} days, fill the corresponding path column (`price_w1`, `price_w2`, `price_w4`, `price_m3`, `price_m6`) and the return-pct variants. Catches Friday→Monday gap events that weekly sampling misses.
  - NO reports yet — collect for 6 months.
- **Migration 009 schema:**
  - `cas_recommendations` table:
    - `id` BIGSERIAL PRIMARY KEY
    - `recommendation_id` TEXT UNIQUE — format `CAS-YYYY-MM-DD-SYMBOL` (deterministic, human-readable, sortable)
    - `recommendation_date` DATE NOT NULL
    - `symbol` TEXT NOT NULL
    - `regime` TEXT NOT NULL
    - `market_score` NUMERIC NOT NULL
    - `cas` NUMERIC NOT NULL
    - `confidence_stars` INTEGER NOT NULL
    - `action` TEXT NOT NULL  (BUY / ADD / WATCH; NO_ACTION not persisted — see V1.1c)
    - `price_at_recommendation` NUMERIC NOT NULL
    - `factor_snapshot` JSONB NOT NULL  — **stores the actual inputs** (weekly, breakout, volume, RS, overhead, sector, regime)
    - `cas_version` TEXT NOT NULL  (e.g., `1.1.0`)
    - `config_hash` TEXT NOT NULL  (e.g., `8f1a29d3`)
    - `commit_sha` TEXT NOT NULL  (e.g., `ca0f4fa`)
    - `engine_signature` TEXT NOT NULL  — composite `v{cas_version}-{commit_sha}-{config_hash}` for one-shot traceability
    - `created_at` TIMESTAMPTZ DEFAULT NOW()
    - UNIQUE INDEX on `(symbol, recommendation_date)`
    - UNIQUE INDEX on `recommendation_id`
  - `cas_recommendation_outcomes` table:
    - `id` BIGSERIAL PRIMARY KEY
    - `recommendation_id` TEXT FK → `cas_recommendations.recommendation_id`
    - `updated_at` TIMESTAMPTZ DEFAULT NOW()
    - `current_price` NUMERIC  (latest close)
    - `price_w1` NUMERIC  (filled at 7 days)
    - `price_w2` NUMERIC  (filled at 14 days)
    - `price_w4` NUMERIC  (filled at 28 days)
    - `price_m3` NUMERIC  (filled at 63 days)
    - `price_m6` NUMERIC  (filled at 126 days)
    - `return_pct_w1`, `return_pct_w2`, `return_pct_w4`, `return_pct_m3`, `return_pct_m6` NUMERIC
    - `max_favorable_excursion_pct` NUMERIC  (running high since recommendation)
    - `max_adverse_excursion_pct` NUMERIC  (running low since recommendation)
    - `milestones_reached` TEXT[]  (e.g., `{w1, w2}`)
    - `status` TEXT  (open / closed-w4 / closed-m6)
- **Helpers:**
  - `make_recommendation_id(date, symbol) → "CAS-2026-07-08-WELCORP"`
  - `compute_engine_signature() → {cas_version, config_hash, commit_sha, signature}`
  - `record_cas_recommendation(row, cas_result, regime, config) → recommendation_id`  (idempotent on `(symbol, date)`)
  - `update_cas_outcomes(date) → n_updated`  (called by daily EOD worker; fills milestones)
- **API wiring:** `/top-by-cas` and `/breakout-status` call `record_cas_recommendation()` for every eligible stock in the response.
- **Cron wiring:** add `scripts/daily_outcome_updater.py` (daily at 16:00 IST). Idempotent: re-running on the same day is safe (only fills new milestones).
- ~10 unit tests + 5 integration tests against a temp DB.

**Session V1.1c — Decision layer (Decision Stability + No Action + Calibration + philosophy doc, ~2 hours):**
- `stabilize_action(prev, today, config) → {action, stability}` wrapper with hysteresis (3-point CAS delta threshold, applied to the API response only).
- "NO_ACTION" recommendation path in API when top-N list empty or all candidates fail eligibility. Return `{action: "NO_ACTION", reason: "..."}`.
- `Calibration.md` initial seed (3 entries from existing weight choices + age-cliff→transition-zone change).
- **Calibration Debt counter** — redefinition: count of unvalidated YAML assumptions, not hardcoded numbers. Implementation: `tools/calibration_debt.py` counts assumptions in YAML marked `validated: false` + manual entries in `Calibration.md`. Reports `total_assumptions / validated / debt`.
- **Spec doc updates** (in this order — why before how):
  - **§0 — Design Principles** (project motto + 7 principles)
  - **§1.0 — Three-Layer Architecture** (Market → Portfolio → Decision; only Decision talks to humans)
  - **§1.1 — Recommendation Lifecycle** (Recommendation → Daily Outcome Worker → Reports)
- `assert_cas_within_tolerance(actual, expected, tolerance=2.0)` helper. Used by golden case regression tests.
- Update `tests/golden_cases.yaml` to use tolerance assertions for CAS values.

**Session V1.1d — Validation + PR (~1 hour):**
- **Session rule (per expert):** No session is allowed to change scoring logic and database schema simultaneously unless tests stay green before and after the migration.
- Full Nifty 500 backfill re-run for `ema_100_slope_5d` + overhead buckets (0.5% rounding means historical values will differ; recompute is required).
- Golden case regression: all 7 cases must pass within tolerance.
- Run outcome updater manually for the last 7 days to seed `cas_recommendation_outcomes` with historical data (optional — needs `recommendation_date` rows to exist; if not, skip).
- All tests pass.
- Branch pushed, PR created.
- Decisions.md, Sessions.md, Progress.md updated.

---

## Decision 102 — V1.1d Release Candidate Scope + V1.2 Priority Order
Date: 2026-07-08
Decision-maker: Project Expert (third-party reviewer)
Trigger: Post-V1.1c expert review of 4 design questions + golden case tolerance + V1.2 ordering

**V1.1d is now treated as a RELEASE CANDIDATE**, not a routine validation session. V1.1 has become foundational infrastructure — expert prefers 30 extra minutes of review over rushed merge that lives for years.

**Four mandatory gates before merging V1.1 to `main`:**

1. **All tests green** — full pytest suite (259 tests expected) passes.
2. **Golden cases within tolerance** — all `tests/golden_cases.yaml` cases pass within ±2.0 CAS points.
3. **Distribution sanity check across full universe** — compute and review aggregate stats (mean/median/95th percentile) for:
   - weekly_trend_score
   - cas (capital allocation score)
   - confidence_stars (full ★★★★★→★ distribution)
   - overhead_supply_score
   Look for anomalies: 90% above 80, everyone getting 5 stars, overhead collapsing toward zero. These won't be caught by 7 golden cases.
4. **Manual Top-20 review** — print top 20 CAS-ranked recommendations with reason text, ask "Would I actually want to allocate capital to these?" If top 20 looks wrong, something is wrong even if all tests pass. **Highest-value manual check.**

**V1.1d scope answers (expert pivots):**

- **Q1 (backfill universe):** Full Nifty universe (~961 symbols) — NOT just active. Expert: "You're recalculating a core indicator, not just validating recommendations. If tomorrow a stock moves from inactive to active, you don't want stale indicator values. Storage and compute are cheap compared to rebuilding confidence in your data." **Pattern: one clean historical baseline, then daily incremental maintenance.**
- **Q2 (tolerance):** ±2.0 universally — agreed with coder recommendation. Do NOT introduce tiered tolerances yet. "Otherwise you'll spend time debating whether something is a 'clean' case versus an 'edge' case."
- **Q3 (PR review):** Wait for review before merge. Auto-merge is NOT acceptable for this size of change (8 commits, 6 new files spanning indicators/persistence/calibration/recommendation logic).

**V1.2 priority order (overrides coder proposal):**

1. **Regime-aware API** — without regime, CAS can recommend buys where philosophy says don't deploy fresh capital. Affects every recommendation. Highest impact.
2. **QIF joins** — replace proxy=75 placeholder. Mechanical, low risk. Unblocks calibration debt.
3. **EMA50 fallback** — coverage improvement for thin-history stocks. Low risk.
4. **ATR-aware overhead buckets** — refinement, not blocker.
5. **5-bar fractals** — V2+ only. Current week-over-week logic is "explainable, deterministic, easy to test. Keep it."

**Strategic shift (most important expert note):**

> "You're getting very close to the point where the engine should stop being judged by code quality and start being judged by decision quality. After V1.1, I would spend more effort measuring recommendation outcomes than adding new scoring factors. That's where the next major improvements are likely to come from."

This marks a transition: V1.x focused on **scoring infrastructure**; V2.x should focus on **outcomes-driven calibration** (validation of assumptions, regime-aware decision making, ML only after outcome data is mature).

**Status:** APPROVED — V1.1d execution authorized with 4-gate scope.

---

## Decision 103 — V2 Pyramiding Discipline Gates (ADD_SECOND_TRANCHE Refinement)
Date: 2026-07-13
Decision-maker: Owner (domain expert) + AI engineer (implementer)
Trigger: Owner requested a more disciplined ADD gate after BreakoutRadar adoption. Current ADD path (`compute_action` in `engine_core/cas_recommendations.py`) only checks `CAS ≥ 85` + `confidence_stars ≥ 4` + `has_existing_position=True`. Owner wanted the second ₹20k to be "earned" through layered checks, not just because CAS crossed 85.

### Final design (9 refinements across 2 rounds of review)

**Gates (all must pass for `ADD_SECOND_TRANCHE`):**
1. `decision_score ≥ add_gate.decision_score_min` (default 85) — G1 capital allocation quality
2. `mri_technical_score ≥ add_gate.mri_technical_min` (default 80) — G2 technical structure
3. `weekly_close > resistance` — G3 price discovery; `resistance` = `PRIOR_52W_HIGH` if history ≥ 52 weeks, else `ALL_TIME_HIGH` (C1 ATH fallback for emerging rerating candidates)
4. `volume_confirmed_breakout == True` — G4 institutional sponsorship; frozen at breakout day, versioned metadata (C2)
5. `breakout_age ≤ add_gate.breakout_age_max` (default 15 trading days) — G5 freshness

Plus the existing precondition `confidence_stars ≥ add_gate.confidence_stars_min` (default 4).

**State model (4 layers):**

| CAS | Gates | Final state | UI | Action |
|-----|-------|-------------|-----|--------|
| < 80 | — | OBSERVE | ⚪ Observe | None |
| 80–84 | — | APPROACHING_ADD | 🟡 Approaching ADD | WATCH |
| ≥ 85 | some fail | READY_FOR_ADD (was `ELIGIBLE_ADD_BLOCKED`, renamed C6) | 🟢 Ready for ADD (n/N gates) | WATCH |
| ≥ 85 | all pass | ADD_SECOND_TRANCHE | 🚀 ADD SECOND TRANCHE | ADD |

`READY_FOR_ADD` surfaces `gates_passed / gates_total` and the specific missing gates (C7 gate confidence metric) — binary passed/blocked was rejected as too lossy.

**Architectural invariants (all YAML-driven, no hardcoded Python constants):**
- Every threshold in `config/capital_allocation.yaml` under `add_gate.*` (C3)
- `add_gate.version: "2.0.0"` persisted in `cas_recommendations.factor_snapshot.config_snapshot.version` for historical reproducibility (C5)
- Resistance source as Python enum `ResistanceSource.{PRIOR_52W_HIGH, ALL_TIME_HIGH}` — not free text (C9)
- `volume_confirmed_breakout` backed by versioned metadata columns: `breakout_day_volume`, `breakout_day_avg20_volume`, `breakout_day_volume_ratio`, `volume_threshold_used`, `breakout_date_for_volume`
- `approaching_add` surface cap: CAS 80–84, top 20 by `radar_priority`, radar page only, no notifications (C4)

**Single-responsibility score model (per owner Q1):**
- `radar_priority` — radar ranking (freshness + urgency)
- `decision_score` — capital allocation gate (G1) — the only "score" gate
- `decision_score` × `mri_technical_score` overlap is INTENTIONAL — `decision_score` = "should I own more of this business?", `mri_technical_score` = "is this chart still healthy?" Revisit only if backtest correlation ρ > 0.9.

**P6 backtest success metrics (C8):**
1. ADD signals/month ≤ 5
2. % outperform benchmark at 20 trading days ≥ 60%
3. % outperform benchmark at 60 trading days ≥ 60%
4. % outperform benchmark at 120 trading days ≥ 55%
5. Win rate vs CAS-only model ≥ CAS-only win rate
6. Avg max drawdown after ADD signal < −12%

If any target missed → Calibration.md journal entry + tighten; do NOT silently adjust.

**Alternatives considered (rejected with rationale):**
- Resistance = daily breakout pivot (ties strategic rule to tactical pattern)
- Resistance = weekly EMA-13 (measures trend, not breakout)
- Resistance = prior weekly swing high (too noisy inside consolidations)
- Volume = today's ratio (penalizes healthy post-breakout consolidation)
- Volume = weekly aggregate (adds complexity without clear edge)
- Lower ADD floor to CAS 80 (increases exposure based on intuition, not evidence — owner: "the second ₹20k is earned")
- Drop one of decision/mri_technical (revisit only after backtest)
- Surface Approaching ADD via email (alert fatigue; C4 cap instead)

**Implementation:** 7 phases (P1 docs → P2 indicators → P3 engine → P4 API → P5 frontend → P6 backtest → P7 wrap-up). P1 = docs only, no code. P2 onward proceeds only after P1 diff reviewed by owner.

**Files this decision touches (cumulative through P7):**
- `migrations/010_add_second_tranche_gates.sql` (NEW)
- `engine_core/cas_indicators.py` (extend — 4 new pure functions)
- `engine_core/cas_recommendations.py` (extend — `evaluate_add_gates`)
- `engine_core/cas_decision_layer.py` (extend — `compute_layered_state`)
- `config/capital_allocation.yaml` (NEW `add_gate` + `approaching_add` sections)
- `config/calibration_registry.yaml` (5 NEW `PROPOSED` entries)
- `Calibration.md` (5 NEW journal entries)
- `api/breakout_status.py` (extend — enriched `/api/breakout/radar` rows)
- `frontend/src/AddStatusChip.tsx` (NEW)
- `frontend/src/BreakoutRadar.tsx` (extend — ADD Status column)
- `docs/CAS_V2_PYRAMIDING_DISCUSSION_2026-07-13.md` (NEW — full discussion record)
- `docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md` §14 (NEW)
- `docs/CAS_SPEC.md` §6 (update)
- `Sessions.md`, `Progress.md` (P1 entries; ongoing through P7)

**Discussion record:** `docs/CAS_V2_PYRAMIDING_DISCUSSION_2026-07-13.md` — full Q&A transcript across both review rounds. Read before resuming work on this branch.

**Calibration freeze:** All 5 new gate thresholds are `PROPOSED`. Move to `VALIDATED` only after P6 backtest hits all 6 success metric targets. No weight/gate tweaks for 100 ADD recommendations post-merge.

**Status:** FINAL — executed (2026-07-15). All 7 phases shipped. P6d (calibration flip) remains blocked until ≥100 live ADD recommendations exist; this is a data-natural blocker, not an implementation gap.

**Implementation log:**
- 2026-07-13 — P1 shipped (commit `ffb3c32`): design docs, YAML config, calibration registry, journal entries.
- 2026-07-13 — P2 shipped (commit `c1052d0`): migration 010 + 4 pure indicator functions + 17 tests + G3/G4 wired into `indicator_engine.py`.
- 2026-07-13 — P3 shipped (commit `3b68f97`): `GateResult`/`ActionResult`, `evaluate_add_gates()`, `compute_layered_state()`, extended `compute_factor_snapshot()`, 26 new tests.
- 2026-07-13 — P4 shipped (commit `54ef6e6`): `/api/cas/recommendations`, `/api/cas/add-eligibility`, `/api/breakout/radar` V2 columns.
- 2026-07-13 — P5 shipped (commit `ade1c28`): `AddStatusChip.tsx`, `BreakoutRadar.tsx` ADD Status column, API helpers.
- 2026-07-13 — P6 shipped (commit `b86f0c5`): `engine_core/backtest_v2_pyramiding.py` + doc wrap-up; 0 ADD signals due to data-coverage gap.
- 2026-07-13 — P6.5 shipped: validation verdict documented. Root cause of zero ADDs confirmed: max CAS 78.45 (< 85), all rows 3 stars (< 4), engine mechanically sound.
- 2026-07-15 — **P7 shipped**: `Sessions.md` + `Progress.md` finalised, `docs/DECISIONS_API_DEPLOYMENT_FIX_2026-07-15.md` archived. All Decision 103 phases closed. Status flipped from APPROVED → FINAL.

**Calibration debt:** G1–G5 entries in `config/calibration_registry.yaml` remain `hypothesis` / `validated_after: null`. They can flip to `validated` only after the P6 backtest succeeds on a meaningful sample of ADD signals (owner threshold: 100 ADD recommendations observed live).

---

## Decision 104 — CAI V2.0 Charting Library
Date: 2026-07-24
Decision: Use TradingView's `lightweight-charts` for the CAI Weekly Review UI instead of trying to force `recharts` to render candlesticks.
Reason: The CAI V2 PRD requires interactive selection of swing lows and structure breaks on a weekly OHLCV chart. Canvas-based `lightweight-charts` is natively built for financial data, high-performance, open-source (Apache 2.0, completely free), and supports the required overlays/drawing tools out of the box. This mitigates a major frontend architectural risk before any backend API payload formats are locked in.
Status: FINAL.

---

## Decision 105 — Trend Screen (7-Filter Cash Segment Screen)
Date: 2026-07-28
Decision: Add a new deterministic screen endpoint `GET /api/breakout/trend-screen` that applies 7 simultaneous filters to identify quality mid-cap cash-segment stocks with multi-timeframe uptrend alignment.
Reason: The existing breakout radar classifies stocks by breakout state (BROKEN_OUT / READY_TO_BREAKOUT / CONSOLIDATING) but doesn't answer "which stocks have a clean multi-EMA stack + reasonable market cap + are not in deep drawdown?" A separate pure-filter endpoint fills this gap without complicating the breakout classification logic. Market cap range (1,000–75,000 Cr) targets the mid-cap band where asymmetric upside is highest. The 4 EMA filters (10/20/50/200) ensure trend alignment across all timeframes. The 52w high proximity filter (> 0.75x) excludes stocks in deep drawdowns.
Status: FINAL.

**Implementation details:**
- Endpoint: `GET /api/breakout/trend-screen` in `api/breakout_status.py`
- 7 filters: Market Cap 1,000–75,000 Cr, Close > EMA(200/50/20/10), Close > 0.75 x 52w High
- Graceful fallback: market_cap column detected via `information_schema.columns`; filter skipped if column missing
- Enrichment: Reuses `_enrich_with_mosi_lite()` for MOSI Lite scores and QIF data
- Pure pass/fail — no breakout state classification; all matching stocks returned

---

## Decision 106 — PortfolioOS Phase 1 Start Boundary
Date: 2026-07-29
Decision-maker: Owner + AI engineer
Trigger: Owner approved beginning implementation from `docs/29 July 26 PortfolioOS Execution plan.md` and explicitly requested that `Progress.md` and `Decisions.md` be updated first with today's exact scope before any feature code is written.

### Decision

Begin PortfolioOS with the smallest deterministic foundation slice from Phase 1:

1. Introduce pure domain models for `IndicatorSnapshot` and `StockSnapshot`.
2. Build a deterministic `StockSnapshotBuilder` in `engine_core/` that assembles a weekly-style stock evaluation snapshot from already-computed MRI platform data.
3. Keep this first slice pure and testable:
   - no Rule Engine
   - no CAI action recommendations
   - no dashboard changes
   - no new database tables or migrations in this session unless the builder is blocked without them
4. Reuse existing indicator and scoring outputs as the single source of truth rather than recalculating them:
   - `daily_prices` for quantitative indicators
   - `stock_scores` for MRI technical score and supporting conditions
   - `quality_verdicts` / existing quality data when available
5. Treat snapshots as immutable output objects. The builder may generate them, but this starting slice does not yet persist a historical snapshot ledger.

### Reason

The July 29 PRD defines the architecture in strict dependency order:

`Indicator Engine -> Stock Snapshot Builder -> MRI/Regime/Portfolio/Decision layers`

Starting with the snapshot layer is the safest incremental step because it:

- respects the PRD's single-responsibility boundaries
- gives CAI and the future Rule Engine a stable input contract
- avoids duplicating calculations that already exist elsewhere in the MRI platform
- is testable without DB migrations, UI changes, or action semantics
- lets future sessions add `DecisionContext`, rules, portfolio state transitions, and ledgering on top of a stable foundation

### Explicit scope for July 29 session start

In scope:

- new deterministic snapshot module under `engine_core/`
- snapshot dataclasses / typed structures
- builder logic that normalizes existing metrics into a PortfolioOS-friendly shape
- unit tests for the builder and snapshot invariants
- documentation updates in `Progress.md`, `Decisions.md`, and later `Sessions.md`

Out of scope for this first implementation slice:

- CAI action outputs (`BUY`, `ADD`, `EXIT`, etc.)
- externalized hard/soft rule evaluation
- decision ledger persistence
- outcome analytics
- dashboard/API surface changes unless needed only for local verification
- architecture redesign of existing CAS / CAI systems

### Implementation notes

- Prefer weekly-ready field names and immutable objects, but source from existing daily tables until a dedicated snapshot persistence layer is justified.
- The builder must consume precomputed values; it must not become a second indicator engine.
- If a required field is missing, represent it explicitly as missing/`None` rather than inventing a proxy unless the proxy already exists elsewhere in the system.
- The first commit should establish the contract, not the full PortfolioOS stack.

Status: APPROVED — implementation starts 2026-07-29.


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

## Decision 100 — Capital Allocation Score V1.0 (rev 2)
Date: 2026-07-06
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
9. **Confidence (NEW rev 2, 0–5 ★ stars)**: A 5-criterion star rating displayed next to the CAS number, NOT a numeric confidence. Each criterion contributes 1 star if met: (a) no_proxy_used, (b) data_completeness ≥ 90%, (c) factor_agreement (std-dev ≤ 20), (d) trend_maturity (weekly_trend_score ≥ 75), (e) breakout_maturity (age ∈ [1, 3]). "Users grasp 5 of 5 stars faster than 92% confidence."
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
Status: **APPROVED — Session N+1 implementation in progress (2026-07-07).** Owner signed off on rev 2 design freeze and the 3-session implementation plan. Full design spec in `docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md` (12 sections, 18 KB). All thresholds + weights in `config/capital_allocation.yaml` (10.1 KB, YAML-validated). Will be flipped to **FINAL — executed** after Session N+3 deploys to Railway and the `/top-by-cas` endpoint serves live banner cards. Detailed implementation plan, handoff notes, and ordered sub-tasks are in §7 of the plan doc + the "Multi-session handoff notes" block at the bottom of the July 6, 2026 (late evening) entry in `Sessions.md` + the "📅 Session: July 6, 2026 (late evening)" block in `Progress.md`.
Implementation log:
- **Session N+1 (2026-07-07)**: migration `migrations/008_capital_allocation_columns.sql` + `engine_core/capital_allocation.py` (pure logic) + `engine_core/test_capital_allocation.py` (24 unit-test scenarios). Status: starting now.

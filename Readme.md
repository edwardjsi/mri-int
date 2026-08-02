# Market Regime Intelligence (MRI) Platform v2.0

> **From screener → quality framework → living institutional investment dossier.**

MRI is the place where you understand every company you own. It is a quantitative equity intelligence platform for Indian listed equities that transforms scattered reports and technical data into a living, institutional-grade investment dossier for every company in your portfolio. It combines technical momentum scoring, fundamental quality analysis, and GPT-powered forensic extraction—delivering a unified, evidence-backed narrative.

---

## 🎯 What MRI Does

At its core, MRI generates a **Living Investment Dossier** for any stock. 
Every company in your portfolio or watchlist has an evidence-backed dossier that evolves as new MOSI reports are compiled.

| Layer | Output | Frequency |
|-------|--------|-----------|
| **Living Dossier** | A single institutional research page answering: Business, Growth, Risks | On-demand |
| **Market Regime** | Risk-On / Risk-Off / Neutral classification | Daily |
| **MRI Score** | 0–100 weighted technical momentum score | Daily |
| **Quality Verdict** | QIF score (0–100) + category + flags | Daily |
| **Trajectory** | Score velocity + trend direction | Daily |
| **AI Forensic Debate** | BUY/HOLD/AVOID verdict + thesis breakdown | On-demand |
| **STEE Signals** | Breakout entries with stop loss & 2R exits | Daily |
| **PERX Intelligence** | Institutional Re-rating Scan, Lifecycle Classification, Peer Compare | On-demand |

---

## 🏆 The 7-Step Winning Stock Selection System (MRI Score)

Each stock is scored 0–100 across 7 weighted technical criteria:

| Step | Indicator | Weight | Pass Criteria |
|------|-----------|--------|--------------|
| 1 | EMA 50 > EMA 200 | 25% | Uptrend integrity |
| 2 | 200 EMA Slope > 0 | 25% | Long-term momentum bias |
| 3 | RS 90d > 50 | 20% | Outperformance vs Nifty |
| 4 | Close ≥ 6-Month High | 20% | Absolute momentum |
| 5 | Volume ≥ 1.3× Avg | 10% | Institutional confirmation |
| 6 | Close > 10D High | 🚀 | Breakout confirmation |
| 7 | Price Quality ≥ 0.7 | — | Strong close (>70% of day's range) |

**Golden Setup (🚀):** Score ≥ 80 + all conditions pass → 🚀 badge in dashboard

**Score Thresholds:**
- 80–100: High Conviction Buy
- 60–79: Watch List
- 40–59: Hold / Monitor
- < 40: Avoid / Liquidate

---

## 📊 Quality Investor Framework (QIF)

MRI evaluates stocks on 7 fundamental dimensions using financial statement data:

| Agent | Dimension | What It Measures |
|-------|-----------|------------------|
| Revenue Agent | Revenue Quality | Growth consistency, cash conversion |
| Margin Agent | Margin Quality | Operating & net margins, sustainability |
| Leverage Agent | Financial Leverage | Debt/equity, interest coverage |
| Working Capital Agent | WC Efficiency | Cash conversion cycle, receivables/inventory |
| Capital Efficiency Agent | ROCE | Return on capital vs WACC |
| Business Evolution Agent | Growth Trajectory | Margin + ROCE improvement trend |
| Financial Translation Agent | Valuation Context | P/E, EV/EBITDA vs sector peers |

**QIF Categories:** Explosive Improver | Stable Compounder | Turnaround | Value Trap | Distressed

---

## 🧠 AI Forensic Debate Engine (QIL Phase 3)

For any QIF-passing stock, MRI can generate a deep-dive **AI Forensic Debate Report** via GPT-4o-mini:

### What the Debate Analyzes:
- **Guidance vs Reality** — Management claims vs actual numbers
- **Nuances** — Subtle improvements/deteriorations analysts miss
- **Glaring Mistakes** — Past over-promises, capital allocation errors, peer underperformance
- **Verdict** — Score/10, BUY/HOLD/AVOID recommendation + "What would change my mind"

### How to Trigger:
1. Click any stock in the dashboard
2. Click **"AI Forensic Debate"** in the Stock Detail Modal
3. Receive a branded HTML email report in ~2 minutes

---

## 📈 Momentum Swing Trading Execution Engine (STEE)

Rule-based swing trade execution with regime filtering:

| Feature | Specification |
|---------|---------------|
| **Entry** | Close > 10D High + Volume ≥ 1.3× 20D Avg |
| **Stop Loss** | 5D Low or breakout candle low |
| **Risk Per Trade** | 1% of capital |
| **Partial Exit** | 50% at 2R (reward-to-risk) |
| **Trailing Stop** | Exit remaining 50% when Close < EMA 10 |
| **Market Filter** | Only trade in BULLISH or SIDEWAYS regimes |
| **Position Sizing** | Qty = (Capital × 0.01) / (Entry − Stop) |

---

## 🔎 PE Re-Rating Discovery Engine (PERX)

PERX is the institutional orchestration and synthesis layer of MRI. Instead of looking at raw scores in isolation, PERX synthesizes technical momentum, QIF fundamentals, and qualitative debate into a cohesive, institutional-grade research view.

### Key Capabilities:
- **Comprehensive Synthesis:** Aggregates MRI Technical Leadership, STEE Breakout Context, and QIF Fundamentals into a unified PE Re-Rating Score.
- **Compare Mode:** Side-by-side analysis of two companies, automatically highlighting the "Institutional Differential" to easily identify the stronger asset.
- **Sector Intelligence:** Contextualizes a stock's performance by ranking it against immediate peers within its specific industry.
- **Lifecycle & Fragility:** Classifies the company's current market stage (e.g., Explosive Improver, Value Trap) and assesses financial fragility.
- **Automated Delivery:** Formats comprehensive scans into professional PDF memos and delivers them directly to user inboxes via AWS SES.
- **Research Archive:** Maintains a persistent memory of prior scans to track how a company's narrative and metrics shift over time.

---

## 🔄 Daily Pipeline Flow

```
Market Close (4PM IST)
│
├─[1] Ingestion: Fetch EOD prices for Nifty 500
├─[2] Indicators: EMA, RS, ATR, High/Low, Volume
├─[3] Regime: Nifty 50 trend classification
├─[4] Scoring: 7-step MRI Score + QIF verdicts
├─[5] Signals: Generate buy/sell/hold recommendations
├─[6] STEE: Evaluate breakout entries for swing trades
├─[7] Health: Validate NULL counts, drift, coverage
└─[8] Email: Send daily digest to all active clients
```

**Total runtime: ~5–8 minutes** (incremental mode)

---

## 🏗️ Architecture

### Dual-Database Strategy
| Database | Purpose | Cost |
|----------|---------|------|
| **Neon.tech** | Production serving (Serverless Postgres) | Free tier |
| **AWS RDS** | Historical bulk storage (private subnet) | Paused |

### Deployment
| Layer | Technology | Platform |
|-------|------------|----------|
| Backend API | FastAPI (Monolith) | Railway.app |
| Frontend | React + Vite + Tailwind | Served from API |
| Email | AWS SES (Transactional) | — |
| Pipeline | GitHub Actions / Railway cron | — |

### Key Files
```
mri-int/
├── api/                          # FastAPI routers (auth, signals, portfolio, etc.)
├── engine_core/
│   ├── ingestion_engine.py       # EOD data ingestion
│   ├── indicator_engine.py       # Technical indicators
│   ├── regime_engine.py          # Market regime + MRI scoring
│   ├── signal_generator.py       # Score → signal logic
│   ├── swing_execution_engine.py # STEE breakout execution
│   └── email_service.py          # AWS SES email delivery
├── engine_fundamental/
│   ├── collector.py              # Financial statement fetcher
│   ├── agents.py                 # 7 QIF scoring agents
│   ├── pipeline.py                # QIF aggregation pipeline
│   ├── trajectory.py             # Score velocity engine
│   └── portfolio_manager.py      # Kelly Criterion sizing
├── engine_qualitative/
│   ├── debate.py                 # AI Forensic Debate Engine
│   └── extractor.py             # QIL extraction layer
├── scripts/
│   ├── pipeline_cloud.sh        # Daily pipeline orchestrator
│   └── pipeline_health_monitor.py
├── docs/
│   ├── PLUMBING_AND_ORCHESTRATION.md
│   ├── STEE_IMPLEMENTATION_PLAN.md
│   ├── AAE_PRD.md               # Amritkaal Alpha Engine vision
│   └── Progress_April_29_30_2026.md
└── frontend/src/                # React dashboard
```

---

## 🛡️ Data & Security Hardening

| Protection | Implementation |
|------------|-----------------|
| **RDS Safeguards** | `deletion_protection=true`, `prevent_destroy=lifecycle`, `skip_final_snapshot=false` |
| **SQL Injection** | All queries use `psycopg2.sql.Identifier` + parameterized inputs |
| **Connection Leaks** | All DB connections use `with` context managers + `try...finally` |
| **Row Level Security** | RLS enabled on all `client_*` tables in PostgreSQL |
| **Temporal Consistency** | All timestamps use `TIMESTAMPTZ` |
| **64-bit Scalability** | `daily_prices` uses `BIGSERIAL` for billions of rows |
| **Schema Auto-Heal** | `api/schema.py` runs `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` on startup |

> ⚠️ **Critical Rule:** Never run `terraform destroy` without first removing RDS from state (`terraform state rm module.rds.*`). See Decision 026/027.

---

## 📋 Go / No-Go Viability Criteria

The platform proceeds to full SaaS launch ONLY if:

| Metric | Target | vs Nifty |
|--------|--------|----------|
| CAGR | > Nifty CAGR | ✅ Must beat |
| Max Drawdown | < Nifty Max DD | ✅ Must be lower |
| Sharpe Ratio | ≥ 1.0 | — |
| Walk-forward Sharpe | ≥ 0.8 | — |
| Regime Stability | Stable across 3+ regimes | — |
| TC Stress Test | Does not collapse at 2× costs | — |

---

## 🔮 Product Roadmap (Amritkaal Alpha Engine Vision)

AAE extends MRI into a full research and stock-selection platform:

| Phase | Feature | Status |
|-------|---------|--------|
| QIF | 7-agent fundamental scoring | ✅ Live |
| QIL | AI narrative + cross-checks | ✅ Live |
| Debate | Forensic GPT equity analysis | ✅ Live |
| PERX | PE Re-Rating Discovery Engine | ✅ Live |
| AAE V1 | Event-driven research platform | 🔜 Next |
| AAE V2 | Document RAG + structural signals | 📋 Planned |
| AAE V3 | Macro correlation + risk agents | 📋 Planned |

See `docs/AAE_PRD.md` for full product vision.

---

## 📜 Key Decisions (Architecture Log)

| # | Decision | Impact |
|---|----------|--------|
| 026 | RDS cascade destroy incident | Never `terraform destroy -target=module.vpc` |
| 027 | Triple-layer RDS protection | `deletion_protection + prevent_destroy + skip_final_snapshot` |
| 030 | Incremental pipeline | 3.5 hrs → ~8 min daily |
| 033 | Free-tier migration | AWS ($80/mo) → Neon + Railway ($0) |
| 066 | Unified monolith | Single Docker container serves API + frontend |
| 068 | 0–100 weighted scoring | Replaced 0–5 binary model |
| 081 | Inclusive scoring | Golden path criteria relaxed for realistic accumulation |
| 085 | AAE as product vision | PRDE → QIF → QIL → AAE roadmap |

---

## ⚖️ Compliance

MRI is a **structured quantitative decision-support analytics platform**.
It does NOT issue buy/sell signals or execute trades automatically.
All outputs must be accompanied by appropriate investment disclaimers.

---

## 👤 Owner

**Immanuel Santosh**
- Solo developer — Full-stack + AWS DevOps
- Location: Tirunelveli, Tamil Nadu, IN
- AWS Region: ap-south-1 (Mumbai)
- Build: LLM-assisted, module-by-module

# MRI Software — Complete Dashboard Guide

**Date:** 2026-07-15
**Audience:** Someone who knows little to nothing about stock investing
**Purpose:** Explain every part of the MRI dashboard in plain language

---

## What is MRI?

MRI stands for **Market Regime Intelligence**.

Think of it as a robot analyst that scans the entire stock market every day. It looks at technical data (price movements, trading volume, trends) and decides:

1. **Is the market in a good mood or a bad mood?** (Market Regime)
2. **Which stocks are worth your attention today?** (Signal Generation)
3. **What should you do with each stock?** (Recommendations)

The result is a dashboard — a single screen that tells you what is happening and what to do. You don't need to analyse 20 different websites. MRI does the work for you.

---

## The Main Screen: Dashboard (🏠)

**Page title:** Signal Dashboard

**What you see when you log in:**

A single page with multiple sections stacked top to bottom. Each section answers a different question about the market and your portfolio.

### Section 1: Market Regime Banner

**What it shows:** A coloured bar at the top that says one of three things:

- **🟢 BULLISH** — The market is healthy. Good time to buy stocks.
- **🟡 SIDEWAYS** — The market is confused. Stocks aren't clearly going up or down. Be careful.
- **🔴 BEAR** — The market is falling. Most stocks are losing value. Best to stay in cash or sell.

**What it means:** This is your weather report. You wouldn't go sailing in a hurricane. Similarly, MRI tells you whether the current market is safe to trade or not.

**How it decides:** MRI looks at whether the Nifty 500 index (a basket of the 500 biggest Indian companies) is trading above or below its key moving averages (more on those later) and whether the trend is up or down.

### Section 2: Daily Summary

**What it shows:** Key numbers about your portfolio today:
- Overall portfolio value
- Today's gain or loss
- Total gain or loss since you started
- Number of positions you're holding

**What it means:** A quick snapshot of "how am I doing?" You don't need to check five different accounts. MRI shows it all in one place.

### Section 3: Today's Signals

**What it shows:** A table of stocks that MRI thinks are worth buying today. Each row shows:

- **Stock name** (e.g. "RELIANCE", "TCS")
- **MRI Score** (0-100) — how good this stock looks right now
- **Price**
- **Score Breakdown** — the 7 conditions that make up the score (see below)
- **Action buttons** — "BUY", "SKIP", "WATCH"

**What it means:** MRI has done its homework. These are the stocks that passed all its filters. You can click BUY if you want to invest, SKIP if you're not interested, or WATCH to track it later.

### Section 4: The 7 Conditions (MRI Score Breakdown)

Each stock gets a score from 0 to 100. The score comes from 7 questions, each with a different weight:

| # | Question | Weight | Plain English |
|---|----------|--------|---------------|
| 1 | Is the 50-day average price above the 200-day average? | 25% | Is the stock in a long-term uptrend? If the short-term trend is above the long-term trend, the stock is heading up. |
| 2 | Is the 200-day average sloping upward? | 25% | Is the long-term direction actually up, not just sideways? A flat 200-day average means the stock isn't really going anywhere. |
| 3 | Has the stock outperformed the market in the last 90 days? | 20% | Is this stock doing better than other stocks? If the whole market is up 5% and this stock is up 15%, that's strong. |
| 4 | Is the price near its 6-month high? | 20% | Is the stock making new highs? Stocks near their highs tend to keep going up (momentum). |
| 5 | Has the stock broken above its 10-day high? | 🚀 | Is the stock breaking out right now? This is a bonus indicator. |
| 6 | Is trading volume at least 1.3× the average? | 10% | Are more people than usual buying this stock today? High volume confirms the move is real. |
| 7 | Did the stock close near the top of its daily range? | — | Did the stock finish the day strong? A stock that opens low but closes high shows buying pressure. |

**Score thresholds:**
- **80-100:** High Conviction Buy (strong buy signal)
- **60-79:** Watch List (interesting but not urgent)
- **40-59:** Hold / Monitor (neutral)
- **<40:** Avoid / Liquidate (stay away or sell)

**What it means:** Instead of looking at 7 different charts, you get one number. 96 means the stock is in excellent shape. 32 means something is wrong.

### Section 5: Pending Signals

**What it shows:** Stocks you flagged earlier but haven't acted on yet. Maybe you marked them as "WATCH" and now MRI is reminding you to decide.

### Section 6: Quality Improvers

**What it shows:** Stocks whose fundamental quality (not price, but the health of the business) is improving. These are companies that are getting stronger — better profits, lower debt, better management.

**What it means:** These are "hidden gems" — stocks that might not look great on price charts yet but are quietly becoming better businesses. MRI flags them so you can investigate before the rest of the market notices.

### Section 7: Trajectory Alerts

**What it shows:** Stocks whose MRI score is changing rapidly — either getting much better or much worse.

**What it means:** If a stock's score jumps from 65 to 92 in one week, something important happened. MRI alerts you so you don't miss the move.

### Section 8: Your Positions

**What it shows:** A table of all stocks you currently own, with current price, your purchase price, profit/loss, and the current MRI score.

**Stock Detail Modal (Click any stock)**

When you click a stock name (anywhere in the dashboard), a popup opens showing:
- **Detailed MRI Score** — the full 7-condition breakdown
- **Quality Score** — how good the company's financial health is (profitability, debt, growth)
- **Price chart** — a small chart showing recent price action
- **AI Forensic Debate** — a button that generates a detailed report (costs a few cents to run)

---

## Page 2: Swing Momentum (🔄)

**Page title:** Swing Momentum (Shadow Picks)

**What it does:** Shows the **top 10 highest-scoring stocks in the entire market**, regardless of what the market is doing.

**Why it exists:** In a bear market (🔴), most stocks look bad. But some stocks still go up even when the overall market is falling. This page finds those stocks.

**The trading rule displayed on the page:**
> In a BEAR market, only buy stocks tagged with 🚀 BREAKOUT. This ensures the stock is actively clearing a ceiling with high volume before you jump in.

**What it means:** These are aggressive picks. In normal markets, you'd stick to the Dashboard signals. In weak markets, Swing Momentum finds the rare stocks that are strong enough to rise against the tide.

**Breakout Badge (🚀):** Stocks that are breaking out of a price ceiling with high volume get a special badge. This is MRI's strongest short-term signal.

---

## Page 3: History (📋)

**Page title:** Trade History

**What it shows:** A list of every action you've taken — every BUY, SELL, ADD, or SKIP — with dates, prices, and profit/loss.

**What it means:** A log of every decision. You can look back and see: "I bought this stock on June 15 at ₹1,200. I sold it on July 10 at ₹1,350. Profit: ₹150 per share."

This is useful for understanding which of your decisions worked and which didn't.

---

## Page 4: Performance (📈)

**Page title:** My Performance

**What it shows:** Charts and statistics about your trading performance over time:
- Portfolio value over time (line chart)
- Win rate (what percentage of your trades were profitable)
- Average profit vs average loss
- Biggest winner and biggest loser
- Monthly returns
- Comparison to the market (benchmark)

**What it means:** MRI doesn't just tell you how stocks are doing. It tells you how **you** are doing. Are you getting better over time? Are your losses smaller than your wins? What's your best and worst trade?

---

## Page 5: Risk Audit (🛡️)

**Page title:** Portfolio Risk Audit

**What it does:** Upload your brokerage statement (Zerodha, Groww, etc.) and MRI analyses your entire portfolio for risk:

- **Concentration risk** — Do you have too much money in one stock?
- **Sector risk** — Are all your stocks in the same industry (e.g. all pharma)?
- **Drawdown risk** — How much would you lose if the market dropped 10%?
- **Correlation risk** — Do all your stocks move in the same direction? (If yes, you're not diversified)
- **Stop-loss gaps** — Which positions don't have a clear exit plan?

**What it means:** Most people own a collection of stocks but have no idea how risky their portfolio actually is. The Risk Audit shows you the weak spots before they cause problems.

---

## Page 6: Watchlist (👀)

**Page title:** Stock Watchlist

**What it shows:** A list of stocks you're tracking but don't own yet. MRI shows the current score for each one so you can see when they become buyable.

**What it means:** You can add stocks here that you heard about, read about, or are curious about. MRI watches them for you and you'll see when their score improves.

---

## Page 7: 112Co Watchlist (🔬)

**Page title:** 112Co Watchlist

**What it shows:** A special list of 112 hand-picked Indian companies that MRI tracks for **PE Re-rating** potential (see PERX page below for what this means).

**What it means:** Not every stock in India is worth following. These 112 are curated by MRI as the most promising mid-to-large cap companies. This is your "master list" of stocks worth knowing.

---

## Page 8: Breakout Radar (🚀)

**Page title:** Breakout Radar

**What it does:** Lists all stocks that are currently in a "breakout" — meaning their price has broken above a key resistance level with high volume.

**What you see:**

- **Each stock's breakout status:**
  - 🆕 FRESH — Just broke out today (most actionable)
  - 🔄 ACTIVE — Breakout is ongoing (still good)
  - ⏪ FROM_YESTERDAY — Broke out yesterday (still tradeable)
  - ⏳ STALE — Breakout happened days ago (less urgent)
  - ❌ FAILED — Breakout didn't hold (avoid)

- **CAS Score** — Capital Allocation Score (0-100). Ranks breakouts by which one deserves your money most right now.

- **ADD Status** — A small coloured badge next to each stock:
  - ⏳ **Observe** (grey) — CAS too low, don't add yet
  - 👀 **Approaching Add** (blue) — Getting closer, watch
  - ⚡ **Ready For Add** (yellow/amber) — Almost there
  - ✅ **Add 2nd Tranche** (green) — This stock has earned a second ₹20,000

**Click on the ADD badge** → A large popup opens showing:
- CAS score and action
- Whether you already own it
- 5 gates (checkpoints) — each is PASS or FAIL
- A progress bar showing how many gates passed
- "What needs to improve" — if some gates failed, it tells you exactly what

**What it means:** When a stock first breaks out, you can buy the first ₹20,000 (first tranche). But should you buy more? The ADD Status column answers that. MRI checks 5 conditions (the "gates") to decide if the stock deserves more money. If all 5 gates pass and confidence is 4★ or higher, the chip turns green ✅ and you can safely add the second tranche.

**Capital Allocation Score (CAS) Banner:**

At the top of the page, a smaller section shows the **Top 5 breakouts by CAS score**. This answers the question: "If I have cash to deploy today, which breakout deserves it most?" CAS considers:
- MRI Score
- Breakout freshness
- Volume confirmation
- Resistance quality
- Existing position (prefer stocks you already own?)

---

## Page 9: PERX (🏛️)

**Page title:** PERX Institutional Scan

**What it stands for:** **PE Re-Rating** — a fancy term that means "the stock market is starting to value this company more highly."

**What it does:** Scans all stocks for signs that institutions (mutual funds, banks, foreign investors) are starting to buy them in a meaningful way.

**What it means in plain language:**

Think of a stock's price as having two parts:
1. **Earnings** — How much profit the company makes
2. **Valuation** — How much investors are willing to pay for those profits

When valuation goes up (PE expands), the stock price goes up even without better earnings. PERX detects when this is starting to happen — before the crowd notices.

**Tabs on this page:**
- **Scan** — Run a fresh scan of all stocks for PE re-rating signals
- **Compare** — Compare two stocks side by side
- **Archive** — View past scan results

---

## Page 10: Expansion Lens (📈)

**Page title:** PE Expansion Report

**What it does:** A detailed report for a specific stock showing:
- Current PE ratio vs historical PE
- Sector average PE
- Is PE expanding or contracting?
- What's driving the re-rating?
- Risks to the re-rating

**What it means:** If you're considering a stock, this report tells you whether the stock is cheap (good value) or expensive (overpriced) compared to its own history and its competitors.

---

## Page 11: AAE Console (🧬)

**Page title:** AAE Console

**What it stands for:** **Aggressive Re-rating Evaluation** — finding stocks that are in the early stages of a major upward revaluation.

**What it shows:**
- **Sourcing Agent** — finds potential candidates for re-rating
- **Macro Agent** — checks if the broader economy supports the re-rating
- **Structural Signal Agent** — looks at company-specific factors (management changes, new products, industry shifts)
- **Execution Monitoring Agent** — tracks whether the re-rating is actually happening

**What it means:** AAE is MRI's most advanced engine. It tries to find the next big winner — a stock that could double or triple — by identifying companies that are fundamentally changing. Think of it as the "multibagger hunter."

---

## Page 12: Unified Scan (🧠)

**Page title:** Unified Institutional Scan

**What it does:** Combines all of MRI's analysis engines into a single report for one stock. You type a stock name and MRI returns:

- **MRI Score** — Technical momentum
- **Quality Score** — Business fundamentals
- **PE Re-rating Signal** — Is the valuation changing?
- **AAE Signal** — Is there an aggressive re-rating setup?
- **Guidance Assessment** — Does management keep its promises?
- **Conviction Rating** — Overall conviction (0-100)

**What it means:** This is the "everything report." Instead of jumping between 5 different pages, you get the complete picture of one stock in one place.

---

## Page 13: GuidanceCheck (🔍)

**Page title:** Management Credibility

**What it does:** Checks whether a company's management team keeps its promises.

**How it works:**
1. MRI reads the company's past statements and guidance (what management said they would achieve)
2. Then checks the actual financial results (what really happened)
3. Calculates a **credibility score** based on how often management was right vs wrong

**What it means:** Some management teams consistently overpromise and underdeliver. Others are conservative and beat their targets. GuidanceCheck tells you which type you're dealing with before you invest. A low credibility score is a red flag.

**Also includes:**
- **Management Integrity Surface** — A deeper look at management behaviour
- **AI Forensic Debate** — AI-generated debate (bull case vs bear case) for the stock's guidance history

---

## Page 14: Conviction Engine (🧠)

**Page title:** Conviction Engine

**What it does:** Takes all the stocks MRI knows about and ranks them by "conviction" — a combined score that considers:
- Technical score (MRI Score)
- Fundamental quality (QIF)
- Management credibility (GuidanceCheck)
- PE re-rating potential (PERX)
- AAE signals

**What it means:** This is MRI's final answer to the question "What should I buy?" It's the master ranking. Everything MRI knows about every stock is distilled into one sorted list.

---

## Page 15: Platform Intelligence (🛡️)

**Page title:** Platform Intelligence

**Visibility:** Only visible to the system administrator

**What it shows:**
- API health (are the servers running?)
- Database health (is the data loading correctly?)
- Pipeline status (have today's scans completed?)
- Error logs
- User statistics
- Data quality metrics

**What it means:** This is the "engine room" — behind-the-scenes information about whether the system itself is working properly. Regular users don't need to check this.

---

## The Stock Detail Modal (Click any stock name)

When you click a stock name anywhere in the dashboard, a popup opens with:

### Tab 1: MRI Score Details
- The 7-condition breakdown with pass/fail for each
- Score trajectory (how the score has changed over time)
- Volume analysis

### Tab 2: Quality (QIF)
- The Quality Investor Framework score (0-100)
- Revenue quality, margin quality, leverage, working capital, capital efficiency
- Business evolution (is the company improving?)
- Category: Explosive Improver, Stable Compounder, Turnaround, Value Trap, or Distressed

### Tab 3: Price Chart
- A small chart showing recent price action
- Volume bars below

### Tab 4: AI Forensic Debate
- Click the button to generate an AI debate report
- The AI analyses the stock and creates a bull case (reasons to buy) and bear case (reasons to sell)
- It gives a verdict: BUY / HOLD / AVOID with a score out of 10
- The report is emailed to you as an HTML document (costs ~$0.002 to generate)

### Tab 5: PERX Report
- PE re-rating analysis for this specific stock
- Peer comparison

### Tab 6: Management Credibility
- GuidanceCheck results for this stock
- Past promises vs actual results

---

## How Everything Connects

Think of MRI as a funnel:

```
All 500 companies in the Nifty 500
                ↓
       MRI scores every stock (0-100)
                ↓
     Dashboard shows today's best signals
                ↓
    You buy ₹20,000 of a stock (first tranche)
                ↓
    Swing Momentum tracks daily performance
                ↓
   Breakout Radar shows breakout status + ADD eligibility
                ↓
   AddStatusChip tells you when to buy ₹20,000 more
                ↓
   PERX / AAE / Conviction Engine provide deeper analysis
                ↓
   GuidanceCheck warns you if management is unreliable
                ↓
        Risk Audit checks your portfolio health
                ↓
         Performance tracks your results
```

Each page serves one purpose. You don't need to look at all of them every day. Most days, you check:

1. **Dashboard** (2 min) — See today's signals and your positions
2. **Breakout Radar** (1 min) — Check which breakouts deserve a second tranche
3. **PERX** (occasionally) — Check for new institutional interest
4. **Conviction Engine** (occasionally) — See the master ranking

The rest are deep-dive tools you use when specific questions arise.

---

## Glossary (Plain English)

| Term | What it means |
|------|---------------|
| **Stock** | A small piece of a company. If you own one share of Reliance, you own a tiny piece of Reliance. |
| **Portfolio** | All the stocks you own, considered together. |
| **Position** | One stock you own. If you own 5 different stocks, you have 5 positions. |
| **PE Ratio** | Price-to-Earnings ratio. How many years of profit you're paying for. PE of 20 means you're paying 20 years' worth of profits. Lower is cheaper. |
| **PE Re-rating** | When investors decide a company is worth more and are willing to pay a higher PE for it. |
| **Breakout** | When a stock's price breaks above a price level where it was stuck before. Like water breaking through a dam. |
| **Volume** | How many shares were traded today. Higher volume = more activity. |
| **Resistance** | A price level where the stock kept hitting and falling back. A ceiling. |
| **Support** | A price level where the stock kept bouncing up. A floor. |
| **Trend** | The general direction of a stock. Up = good. Down = bad. |
| **Moving Average** | The average price over a period (e.g. 50 days). Smooths out daily noise. |
| **EMA** | Exponential Moving Average. Like a moving average but gives more weight to recent days. |
| **Bear Market** | A market that is falling. Generally bad for stocks. |
| **Bull Market** | A market that is rising. Generally good for stocks. |
| **Tranche** | A slice of money. ₹20,000 first tranche = first ₹20,000 you invest. Second tranche = next ₹20,000. |
| **Stop Loss** | A price at which you automatically sell. If you buy at ₹100 and set a stop at ₹80, you sell if it drops to ₹80. Limits your loss. |
| **Trailing Stop** | A stop loss that moves up as the stock rises. If the stock goes from ₹100 to ₹150, the stop moves up too. |
| **Drawdown** | How far a stock has fallen from its peak. ₹100 stock that drops to ₹70 has a 30% drawdown. |
| **Sector** | A group of similar companies. Pharma, Banking, IT, Chemicals are all sectors. |
| **Diversification** | Not putting all your money in one stock or one sector. Spreading risk. |
| **Conviction** | How confident MRI is that a stock is a good buy. Higher = more confident. |
| **Regime** | The market's current mood. Bullish (happy), Sideways (neutral), Bear (unhappy). |
| **Re-rating** | The market deciding a stock is worth more than it was before. |

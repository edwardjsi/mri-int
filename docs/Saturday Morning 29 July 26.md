I actually think this should become **one of the major milestones** for MRI.

Not just a dashboard, but a **Weekly Portfolio Review System**.

The dashboard and email should use the **same underlying data model**. The dashboard is for exploration; the email is for execution.

---

# PRD: Weekly Portfolio Review Dashboard & Email

**Product:** MRI + Capital Allocation Intelligence (CAI)

**Version:** 1.0

**Status:** Ready for Development

**Priority:** High

---

# 1. Vision

Every Saturday morning, the investor should spend **20–30 minutes** reviewing the portfolio and finish with a clear action plan for Monday.

The system should answer one question:

> **"What is the highest-impact capital allocation decision I should make this week?"**

The dashboard and email must present the same recommendations.

---

# 2. Primary User Story

> As an investor, I want MRI + CAI to analyze my portfolio every Saturday morning and tell me exactly what to Buy, Add, Hold, Reduce, Rotate, or Exit, so I don't need to manually analyze every position.

---

# 3. Weekly Review Workflow

```text
Friday Market Close
        │
        ▼
Indicator Engine Refresh
        │
        ▼
MRI Engine
        │
        ▼
CAI Engine
        │
        ▼
Decision Engine
        │
        ├── Update Dashboard
        ├── Store Decision Ledger
        └── Generate Weekly Email
```

---

# 4. Dashboard Layout

## Section A – Portfolio Overview

Display:

* Market Regime
* Portfolio Health Score
* Deployment %
* Cash Available
* Cash Target
* Number of Holdings
* Number of Actionable Decisions
* Last Analysis Timestamp

Example:

```
Portfolio Overview

Market Regime          Bull

Portfolio Health       91

Deployment             74%

Cash                   ₹3.15L

Cash Target            20%

Holdings               18

Action Items           5

Analysis Time          Saturday 08:00 IST
```

---

# Section B – ⭐ This Week's Decision

Largest card on the screen.

Example:

```
THIS WEEK'S DECISION

ADD TO NEULAND LABS

Recommended Amount

₹30,000

Reason

• First tranche earned next tranche

• Weekly trend intact

• MRI Score 95

• CAI Score 94

• Portfolio allocation acceptable

Confidence

95%
```

Only one recommendation appears here.

This is the highest-priority portfolio action.

---

# Section C – Action Queue

Display every actionable holding.

Columns

| Priority | Stock | MRI | CAI | Action | Confidence |
| -------- | ----- | --: | --: | ------ | ---------: |

Actions include:

* BUY
* ADD
* HOLD
* WAIT
* REVIEW
* REDUCE
* ROTATE
* EXIT

Sort by:

1. EXIT
2. REDUCE
3. ADD
4. BUY
5. HOLD

---

# Section D – Holdings Table

Display all holdings.

Columns:

* Ticker
* Quantity
* Avg Price
* Current Price
* P/L %
* MRI Score
* CAI Score
* Current Action
* Next Tranche
* Structure Stop
* Confidence
* Last Reviewed

Example:

| Stock   | MRI | CAI | Action |
| ------- | --: | --: | ------ |
| Divis   |  95 |  94 | ADD    |
| Neuland |  94 |  92 | ADD    |
| Torrent |  90 |  74 | WAIT   |
| Polycab |  96 |  58 | REVIEW |

---

# Section E – Opportunity Queue

Stocks not currently owned.

Columns

* Ticker
* MRI Score
* Entry Status
* Suggested First Tranche
* Notes

---

# Section F – Portfolio Warnings

Examples

```
Portfolio Warnings

Pharma exposure exceeds target.

Three positions close to structure stop.

Cash below target.

Two positions earned next tranche.
```

---

# Section G – Decision Ledger

Display the most recent recommendations.

Columns

* Date
* Stock
* Action
* Followed?
* Current Return
* Outcome

---

# 5. Email Report

Subject

```
MRI Weekly Portfolio Review – 1 August 2026
```

---

## Section 1 – Executive Summary

```
Good Morning.

Market Regime

Bull

Portfolio Health

91

Deployment

74%

Cash

₹315,000

Action Items

5
```

---

## Section 2 – This Week's Decision

```
⭐ Highest Priority

ADD ₹30,000 TO NEULAND LABS

Reason

• First tranche earned next tranche

• Trend intact

• MRI 95

• CAI 94

Confidence

95%
```

---

## Section 3 – Immediate Actions

```
EXIT

CGCL

Reason

Weekly structure broken.

Confidence

99%

--------------------

ADD

DIVIS

₹30,000

--------------------

HOLD

LENSKART

--------------------

WAIT

TORRENT
```

---

## Section 4 – Portfolio Health

```
Portfolio Health

91

Strong Positions

8

Watch List

4

Review Required

2

Exit Candidates

1
```

---

## Section 5 – Opportunity Queue

```
Top MRI Candidates

1. Titan

MRI 98

2. TVS Motor

MRI 97

3. Marico

MRI 94
```

---

## Section 6 – Decision Ledger Summary

```
Last Week

Bought Lenskart

CAI

94

Current Return

+6.2%
```

---

# 6. Notification Rules

Generate an email only if one of the following occurs:

* Weekly review completed (Saturday summary)
* New BUY recommendation
* New ADD recommendation
* EXIT recommendation
* Structure break detected
* Portfolio risk exceeds threshold
* Cash deployment outside target
* New highest-priority decision replaces previous one

---

# 7. User Actions

From the dashboard, the user can:

* Mark recommendation as Executed
* Mark recommendation as Ignored
* Snooze recommendation
* Add notes
* Open full MRI report
* Open Decision Ledger history

---

# 8. API Response Contract

```json
{
  "portfolio_summary": {},
  "highest_priority_decision": {},
  "action_queue": [],
  "holdings": [],
  "opportunities": [],
  "warnings": [],
  "decision_history": []
}
```

The dashboard and email renderer must consume the same API response.

---

# 9. Non-Functional Requirements

* Complete analysis of a portfolio of up to 100 holdings in under 30 seconds.
* Dashboard data and email must be generated from the same analysis run to avoid inconsistencies.
* Every recommendation must be versioned and stored in the Decision Ledger.
* Every recommendation must include a machine-readable rule trace (which rules fired) and a human-readable explanation.

---

# 10. Success Metrics

* Weekly review completed in under 30 minutes.
* Every holding has exactly one current CAI action.
* Every recommendation is recorded in the Decision Ledger.
* Dashboard and email are identical in recommendations.
* The user can identify and execute the highest-priority portfolio decision within one minute of opening the dashboard.

## Recommendation for V1 vs. V2

To keep development focused, I'd split this into two releases:

**V1 (2–3 weeks):**

* Dashboard
* Weekly CAI analysis
* "This Week's Decision"
* Action Queue
* Holdings table
* Portfolio warnings
* Decision Ledger
* Plain HTML email sent every Saturday after the market data refresh

**V2:**

* One-click "Mark Executed"/"Ignored"
* Email digests for mid-week alerts (new EXIT/ADD recommendations)
* Interactive charts and portfolio analytics
* Mobile-friendly dashboard
* Slack/Telegram/WhatsApp notifications
* Historical performance and rule effectiveness analytics

This staged approach gets a complete weekly operating system into your hands quickly, while leaving room to add collaboration, richer notifications, and analytics once the core decision engine has proven itself.

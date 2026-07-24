# CAI V2.0 --- Capital Allocation Intelligence

## Product Requirements Document (PRD)

> **Status:** Canonical Specification
>
> This document defines CAI (Capital Allocation Intelligence), the
> portfolio management workspace inside MRI. MRI discovers
> opportunities. CAI manages positions, capital allocation, portfolio
> decisions and the permanent decision journal.

------------------------------------------------------------------------

# 1. Vision

MRI answers:

-   What deserves attention?
-   What is worth owning?

CAI answers:

-   Should I buy?
-   Should I add?
-   Should I wait?
-   Should I reduce?
-   Should I rotate?
-   Should I exit?
-   Where should my next rupee go?

CAI is not a broker. CAI is not an order management system. CAI is an
Investment Committee.

------------------------------------------------------------------------

# 2. Navigation

    MRI

    Dashboard
    Opportunities
    Watchlist

    CAI
     ├ Portfolio
     ├ Position Review
     ├ Investment Committee
     ├ Decision Ledger
     ├ Replay
     └ Portfolio Analytics

    Settings

------------------------------------------------------------------------

# 3. Core Principles

1.  MRI discovers.
2.  CAI decides.
3.  Weekly charts drive decisions.
4.  Intraday noise is ignored.
5.  Reviews are permanent.
6.  Alerts are temporary.
7.  Decisions are auditable.
8.  Never average down.
9.  Additional tranches must be earned.
10. Every rupee must earn the next rupee.

------------------------------------------------------------------------

# 4. Portfolio Workspace

Each holding displays:

-   MRI Score
-   CAI Position Health
-   Allocation %
-   Tranche Progress
-   Review button

Actions:

-   Review
-   Open Ledger
-   Replay
-   Notes

------------------------------------------------------------------------

# 5. Position Review Workflow

Trigger:

-   Healthy Pullback
-   Breakout
-   Trend Warning
-   Earnings
-   News
-   Manual

Workflow:

1.  Open Portfolio
2.  Click Review
3.  MRI renders weekly chart from OHLCV
4.  User selects swing low (future: automatic suggestion)
5.  CAI computes:
    -   Story Alive
    -   Weekly Trend
    -   Structure Break
    -   Position Health
    -   Tranche Eligibility
    -   Recommendation
6.  Save Review

No screenshots are uploaded or stored.

------------------------------------------------------------------------

# 6. Weekly Chart Engine

Charts are generated dynamically from MRI market data.

Stored:

-   selected candle date
-   swing low
-   structure break
-   annotations
-   review metadata

Images are never persisted.

------------------------------------------------------------------------

# 7. Position Health

Calculated using:

-   trend quality
-   relative strength
-   earnings quality
-   institutional participation
-   drawdown
-   structure integrity
-   allocation risk

Output:

0--100 score.

------------------------------------------------------------------------

# 8. Recommendations

Possible outcomes:

-   BUY
-   ADD
-   HOLD
-   WAIT
-   REDUCE
-   ROTATE
-   EXIT

------------------------------------------------------------------------

# 9. Investment Committee

Every Friday after market close:

Inputs:

-   Portfolio
-   Cash
-   Pending Reviews
-   MRI Scores
-   Allocation Rules

Outputs:

-   ADD
-   HOLD
-   WAIT
-   REDUCE
-   EXIT
-   ROTATE

Committee report is stored permanently.

------------------------------------------------------------------------

# 10. Monday Execution

Monday:

User reviews approved recommendations.

Execute manually.

Decision status becomes:

-   Executed
-   Skipped
-   Deferred

Execution price stored.

------------------------------------------------------------------------

# 11. Decision Ledger

Immutable audit trail.

Stores:

-   recommendation
-   reasoning
-   execution
-   timestamps
-   later outcome

No record is edited. Changes create new records.

------------------------------------------------------------------------

# 12. Replay

Selecting Replay reconstructs the historical weekly chart from OHLCV and
overlays:

-   swing low
-   structure break
-   recommendation

No screenshots required.

------------------------------------------------------------------------

# 13. Database

## Portfolio

-   id
-   owner
-   cash
-   health
-   updated_at

## Position

-   id
-   portfolio_id
-   symbol
-   quantity
-   average_price
-   allocation
-   tranche
-   status

## PositionReview

-   id
-   position_id
-   trigger
-   review_date
-   weekly_candle
-   swing_low
-   structure_break
-   story_status
-   trend_status
-   position_health
-   recommendation
-   notes

## CommitteeReport

-   id
-   week_end
-   created_at
-   approved_at

## CommitteeDecision

-   report_id
-   position_id
-   recommendation
-   amount
-   reason

## DecisionLedger

-   id
-   decision_id
-   execution_status
-   execution_price
-   execution_date

------------------------------------------------------------------------

# 14. APIs

GET /portfolio

GET /portfolio/{id}

POST /review

GET /review/{id}

POST /committee/generate

GET /committee/latest

POST /decision/execute

GET /ledger

GET /replay/{review_id}

------------------------------------------------------------------------

# 15. Business Rules

-   Never add to losing structures.
-   Weekly structure overrides daily signals.
-   Reviews are immutable.
-   Alerts are not stored.
-   Charts are regenerated.
-   Capital allocation follows CAI.
-   Friday decides.
-   Monday executes.

------------------------------------------------------------------------

# 16. Future Enhancements

-   Automatic swing-low detection
-   AI structure validation
-   Portfolio risk engine
-   Capital optimization
-   Scenario simulation
-   Explainable AI recommendations

------------------------------------------------------------------------

# 17. Acceptance Criteria

-   Portfolio visible inside MRI.
-   Review generated without screenshots.
-   Weekly charts generated from OHLCV.
-   Reviews permanently stored.
-   Committee generated every Friday.
-   Decision Ledger fully auditable.
-   Replay reconstructs historical reviews.
-   CAI integrated as a dedicated MRI workspace.

------------------------------------------------------------------------

End of Document.


---

# 3A. Dual Review Architecture (Updated)

CAI has **two distinct review engines** because the questions before and after owning a stock are fundamentally different.

## Candidate Review (Pre-Ownership)

Purpose: Decide whether a stock deserves the **first tranche**.

This review is embedded directly inside every MRI discovery screen:

- STEE
- BreakoutRadar
- 112 Companies

Workflow:

```
Candidate
    ↓
Weekly Chart (generated by MRI)
    ↓
Candidate Review
    ↓
BUY FIRST TRANCHE
WATCH
REJECT
```

Candidate Review evaluates:

- Business story
- Weekly trend
- Structure quality
- MRI score
- Relative strength
- Breakout quality
- Initial risk
- First-tranche eligibility

The output is **not** ADD/HOLD/EXIT. It is:

- BUY FIRST TRANCHE
- WATCH
- REJECT

This reflects the investing philosophy:

> Flirt with many. Marry a few.

Only stocks approved by Candidate Review become portfolio positions.

## Position Review (Post-Ownership)

Purpose: Decide what to do with an existing position.

Available only from the Portfolio workspace.

Workflow:

```
Portfolio
    ↓
Review Position
    ↓
ADD
WAIT
HOLD
REDUCE
EXIT
ROTATE
```

Position Review evaluates:

- Cost basis
- Current tranche
- Position Health
- Weekly structure
- Structure break
- Tranche eligibility
- Capital allocation
- Portfolio concentration
- Cash availability

This review follows the previously defined tranche rules for second and subsequent allocations.

## Complete Investment Lifecycle

```
112 Companies
        ↓
BreakoutRadar
        ↓
STEE
        ↓
Candidate Review
        ↓
BUY FIRST TRANCHE
        ↓
Portfolio (CAI)
        ↓
Position Review
        ↓
Investment Committee
        ↓
Decision Ledger
```

The Portfolio module begins only after the first tranche has been initiated.

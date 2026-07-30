Absolutely. In fact, I think this is a **better design** than what we had before. We've discovered that **REVIEW is not an investment action**—it's a workflow state. Those are different concepts.

This is the PRD I would hand to an engineering team.

---

# PRD: CAI Action Engine v2.0

**Project:** MRI – Capital Allocation Intelligence (CAI)

**Version:** 2.0

**Status:** Ready for Implementation

**Priority:** Critical

---

# Objective

Redesign the CAI recommendation engine so that it produces **true investment actions** rather than forcing unnecessary weekly reviews.

The system should identify **exceptions** that require investor attention while leaving healthy positions alone.

---

# Problem Statement

The current CAI implementation incorrectly labels many profitable, healthy positions as **REVIEW**.

Example:

| Stock      |     P/L | Current Action |
| ---------- | ------: | -------------- |
| Welcorp    | +22.15% | REVIEW         |
| Poonawalla |  +8.16% | REVIEW         |
| Radico     |  +5.44% | REVIEW         |
| Neuland    |  +3.93% | REVIEW         |

This is incorrect because profitability alone is **not** a reason to review a position.

The result is dashboard noise and reduced confidence in the recommendation engine.

---

# Product Philosophy

CAI should answer one question:

> **"What should I do with this position today?"**

It should **not** answer:

> "Should I look at this stock again?"

---

# New Decision Model

The engine must distinguish between:

## Investment Action

The portfolio decision.

Possible values:

```text
BUY
ADD
HOLD
WAIT
REDUCE
ROTATE
EXIT
```

---

## Review Trigger

A separate flag indicating whether human attention is required.

Possible values:

```text
NONE
REVIEW_REQUIRED
URGENT_REVIEW
```

These are **not investment actions**.

They are workflow flags.

---

# New CAI Output

Instead of

```json
{
    "action":"REVIEW"
}
```

The engine should produce

```json
{
    "action":"HOLD",
    "review_status":"NONE"
}
```

Example

```json
{
    "action":"ADD",
    "review_status":"NONE"
}
```

Example

```json
{
    "action":"HOLD",
    "review_status":"REVIEW_REQUIRED",
    "review_reason":"Quarterly results next week"
}
```

---

# Action Definitions

## BUY

Open first tranche.

Conditions:

* MRI qualifies
* Entry criteria satisfied
* Portfolio allocation available

---

## ADD

Deploy next tranche.

Conditions:

* First tranche profitable
* Weekly structure intact
* Allocation below maximum
* Better opportunity does not exist
* Market regime permits adding

---

## HOLD

Default action.

Meaning:

> Continue holding.

No capital changes required.

This should become the most common recommendation.

---

## WAIT

No action today.

Example:

* Breakout not confirmed
* Pullback incomplete
* Capital unavailable

---

## REDUCE

Trim exposure.

Conditions:

* Position overweight
* Risk increasing
* Better opportunity available

---

## ROTATE

Sell one position.

Buy another.

Conditions:

* Existing CAI weak
* New MRI significantly stronger

---

## EXIT

Close position.

Triggered by hard rules.

Examples:

* Weekly structure broken
* Thesis broken
* Stop hit

---

# Review Status

Review is **not** an investment recommendation.

It indicates human attention.

Possible values:

## NONE

No review needed.

Healthy position.

---

## REVIEW_REQUIRED

Investor should examine the position this weekend.

Examples:

* Earnings due
* CAI dropped significantly
* Allocation exceeds target

---

## URGENT_REVIEW

Immediate attention required.

Examples:

* Structure close to breaking
* Hard rule nearly triggered
* Extreme volatility

---

# Review Trigger Rules

The engine should mark REVIEW_REQUIRED only when at least one condition is satisfied.

Examples

## Earnings

Quarterly results within seven calendar days.

---

## Structure Warning

Distance to structure stop less than configurable threshold.

---

## Allocation

Position exceeds configured maximum allocation.

---

## Opportunity Cost

A significantly higher-ranked MRI candidate is available.

---

## Score Deterioration

CAI score falls more than configurable threshold compared to previous review.

---

## Manual Flag

User manually requests review.

---

# Decision Tree

The engine must evaluate decisions in the following order.

```text
Hard Rule Triggered?

↓

YES

EXIT

↓

NO

↓

Review Trigger?

↓

YES

Review Status = REVIEW_REQUIRED

↓

Next Tranche Earned?

↓

YES

ADD

↓

BUY Conditions?

↓

YES

BUY

↓

Reduce Conditions?

↓

YES

REDUCE

↓

Rotate Conditions?

↓

YES

ROTATE

↓

WAIT Conditions?

↓

YES

WAIT

↓

Otherwise

HOLD
```

---

# Dashboard Changes

Replace the existing Action column.

Old

| Stock   | Action |
| ------- | ------ |
| Welcorp | REVIEW |

New

| Stock   | Action | Review |
| ------- | ------ | ------ |
| Welcorp | HOLD   | —      |
| Neuland | ADD    | —      |
| Polycab | HOLD   | REVIEW |
| CGCL    | EXIT   | URGENT |

---

# Email Changes

The weekly email should separate actions from reviews.

Example

## Portfolio Actions

```
ADD

Neuland Labs

₹30,000
```

```
EXIT

CGCL

Weekly structure broken.
```

---

## Review Required

```
Polycab

Quarterly results due next week.
```

```
Poonawalla

Allocation exceeds target.
```

---

# API Changes

Replace

```json
{
    "action":"REVIEW"
}
```

With

```json
{
    "action":"HOLD",
    "review_status":"NONE",
    "review_reason":null
}
```

Example

```json
{
    "action":"HOLD",
    "review_status":"REVIEW_REQUIRED",
    "review_reason":"Quarterly results due"
}
```

---

# Acceptance Criteria

The implementation is complete when:

* REVIEW is no longer a valid investment action.
* HOLD becomes the default recommendation for healthy positions.
* REVIEW is represented exclusively through `review_status`.
* Every review recommendation includes a machine-readable and human-readable reason.
* Dashboard and email clearly separate **investment decisions** from **review requests**.
* Existing profitable positions with intact trends (e.g., Welcorp) display `HOLD` unless a review trigger exists.
* Every recommendation is recorded in the Decision Ledger with both `action` and `review_status`.

---

# Future Enhancements

The engine should be designed so additional review triggers can be added without modifying the core decision logic. Review rules should be configurable (e.g., via YAML or database configuration) and evaluated independently of action selection.

## Architectural Recommendation

I would also ask your AI development team to make one structural change that will pay off over time.

Instead of returning:

```python
action = "HOLD"
```

return a richer decision object:

```python
CAIDecision(
    action="HOLD",
    review_status="NONE",
    confidence=94,
    priority="LOW",
    primary_reason="Weekly trend intact",
    secondary_reasons=[
        "First tranche profitable",
        "No superior MRI candidate available"
    ],
    next_review_date="2026-08-08"
)
```

This gives the dashboard, email generator, mobile app, and Decision Ledger a single, consistent object to consume. As CAI evolves, you can add fields without breaking the rest of the system, making it a much more maintainable architecture.

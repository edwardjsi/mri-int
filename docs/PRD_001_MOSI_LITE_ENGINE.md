# PRD-001: MOSI Lite Engine

## Objective

Improve the quality of MRI 1.0 breakout candidates by automatically filtering technically strong stocks using lightweight fundamental and structural checks.

This feature is NOT intended to replace the full MOSI framework.

It is intended to increase the probability that today's breakout candidates represent institutional-quality businesses.

---

# Problem

Current MRI ranks stocks almost entirely from technical signals.

As a result:

* technically strong but fundamentally weak companies can rank highly
* every breakout appears equally attractive
* users must manually research every candidate

We need a lightweight filter.

---

# Goal

Every stock in Breakout Radar should display:

* MRI Score
* MOSI Lite Score
* Decision Score
* Confidence
* Recommendation

---

# Architecture

Create a new service.

```
services/

mosiLite.ts
```

This service must NOT contain any UI logic.

It only calculates scores.

---

# Inputs

Existing stock object.

Possible fields:

```
symbol

sector

industry

price

52WeekHigh

salesGrowth

profitGrowth

roce

roe

debtToEquity

promoterHolding

marketCap

quarterlyGrowth

technicalScore
```

Do not assume every field exists.

Gracefully handle missing values.

---

# Output

```
{
    mosiLiteScore: number,

    decisionScore: number,

    confidence: "LOW" | "MEDIUM" | "HIGH",

    recommendation:
        "TODAYS_PICK"
        | "RESEARCH"
        | "WATCHLIST"
        | "IGNORE"
}
```

---

# MOSI Lite Scoring

Maximum

100 points.

---

## M — Macro (20)

Sector outperforming market

10

Industry outperforming sector

10

---

## O — Operating Excellence (30)

Sales Growth >15%

10

Profit Growth >15%

10

ROCE >20%

10

---

## S — Structural Quality (30)

Near 52 Week High

10

Stage 2 Trend

10

Quarterly acceleration

10

---

## I — Institutional Quality (20)

Promoter Holding >50%

10

Debt/Equity <0.5

10

---

# Decision Score

```
Decision

=

MRI Technical * 0.60

+

MOSI Lite * 0.40
```

Clamp between

0

100.

---

# Confidence

Start with Decision Score.

Adjust according to market regime.

Example

Bull Market

HIGH

Sideways

MEDIUM

Bear

LOW

For MRI 1.0

Market Regime can initially be a configurable constant.

Future versions will calculate this automatically.

---

# Recommendation Logic

Decision >=90

TODAYS_PICK

Decision 80–89

RESEARCH

Decision 70–79

WATCHLIST

Below 70

IGNORE

---

# UI

Each Breakout Card must display

```
MRI

96

MOSI Lite

91

Decision

94

Confidence

MEDIUM

Recommendation

TODAY'S PICK
```

---

# Sorting

Breakout Radar should sort by

Decision Score

NOT MRI Score.

---

# Engineering Rules

No duplicate business logic.

No hardcoded stock names.

Pure functions only.

No API breaking changes.

Backward compatible.

---

# Tests

Test

ROCE scoring

Sales Growth scoring

Debt scoring

Missing data

Decision Score

Confidence

Recommendation mapping

---

# Future

This service must be designed so that

MOSI Lite

can later be replaced by

Full MOSI

without changing the UI.


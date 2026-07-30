# PRD: MRI Frontend V1

**Version:** 1.0  
**Priority:** P0  
**Design Principle:** Optimize for decision-making, not information display. Every screen must help the user make an investment decision in under 30 seconds. If a feature does not directly improve that goal, defer it to V2.

## 0. Imperative

Build exactly this. No additional features. No polishing. No redesign. Ship the first working version as quickly as possible. We'll refine it after we've used it with a real portfolio.

## 1. Objective
Build the minimum frontend required to review and act on MRI decisions every Saturday.

This is not a production UI. It is a functional interface to validate:
- Decision Engine.
- Explainability.
- Decision Ledger.

Everything else is out of scope for V1.

## 2. User
Single portfolio owner using MRI to review weekly stock decisions.

## 3. Data Contract
The frontend must render only the backend-supported schema for each screen.

- **Dashboard:** weekly recommendations, portfolio summary, portfolio health, market regime, and cash available.
- **Stock Decision:** one recommendation object with action, confidence, summary, rules, and evidence.
- **Decision Ledger:** historical decision records with execution and outcome status.

No frontend business logic. No derived investment logic in the browser.

## 4. Screens

### 4.1 Dashboard
**Purpose:** Answer one question: What should I do this week?

**Display:**
- Portfolio Summary.
- Portfolio Health.
- Market Regime.
- Cash Available.
- Weekly Decisions sorted by priority.

**Interaction:**
- Clicking a recommendation opens the Stock Decision page for that stock.

**Example:**
- ADD ₹30,000 → Neuland Labs.
- HOLD → Welcorp.
- EXIT → CGCL.

### 4.2 Stock Decision
**Purpose:** Explain exactly why MRI made the recommendation.

**Layout:** Accordion sections:
- Recommendation.
- Why.
- Rules.
- Evidence.

**Recommendation displays:**
- Action.
- Confidence.
- One-line summary.

**Why displays:**
- Primary reason.
- Supporting reasons.

**Rules displays:**
- Every evaluated rule with status.

**Evidence displays:**
- Supporting facts used by the decision engine.

**Constraint:** No charts in V1.

### 4.3 Decision Ledger
**Purpose:** Show historical decisions in a simple table.

**Columns:**
- Date.
- Stock.
- Decision.
- Executed.
- Outcome.

**Interaction:**
- Selecting a row opens the associated Stock Decision page.

## 5. Navigation
Only three menu items are allowed:
- Dashboard.
- Portfolio.
- Decision Ledger.

No additional navigation.

## 6. States
The UI must handle:
- Loading.
- Empty data.
- API error.
- Partial data.

## 7. Technical Requirements
- Use the existing MRI/CAI API.
- Use the existing Explanation Tree returned by the backend.
- Render only supported backend fields.
- No frontend business logic.
- No charts.
- No AI chat.
- No mobile-specific work.
- No watchlists, alerts, notifications, sector views, compare mode, or user settings.

## 8. Out of Scope
Explicitly excluded from V1:
- Charts.
- AI Chat.
- Mobile.
- Watchlists.
- Alerts.
- Notifications.
- Portfolio analytics.
- Sector views.
- Compare stocks.
- User settings.

## 9. Acceptance Criteria
The frontend is complete when a user can:
1. Open the Dashboard.
2. See this week’s recommendations.
3. Click any recommendation.
4. Understand why it was generated.
5. Drill into Rules and Evidence.
6. View historical decisions in the Decision Ledger.

If all six tasks work smoothly, V1 is complete.

## 10. Notes
- Keep the UI fast and sparse.
- Prefer readability over decoration.
- Avoid adding any feature that slows weekly decision-making.

## 11. Incorporate this

Change 1

Replace:

Clicking a recommendation opens the Stock Decision page.

With:

Clicking a recommendation opens a right-side Stock Decision Panel. The Dashboard remains visible. Closing the panel returns the user to the dashboard without navigation.

Change 2

Replace:

Navigation

Dashboard
Portfolio
Decision Ledger

with

Navigation

Dashboard
Decision Ledger

Remove Portfolio from V1.

Change 3

Add under Acceptance Criteria:

Every recommendation must include a valid explanation tree. If an explanation cannot be rendered, the recommendation must not be displayed without an explanatory error message.

Change 4

Add at the top:

Success Metric

A user should be able to review a 20-stock portfolio and confidently complete their weekly review in under 10 minutes using only this interface.
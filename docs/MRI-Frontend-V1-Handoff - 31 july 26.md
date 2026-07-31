Absolutely — those are strong improvements, and they make the handoff much safer for an AI coding team. The biggest wins are **North Star**, **Component Ownership**, **NEVER**, **Versioning**, and **Assumptions** because they reduce ambiguity and stop the UI from drifting into business logic. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/8781877/8a49a5ca-586b-4e35-b74c-71008008acec/MRI-Product-Bible.md?AWSAccessKeyId=ASIA2F3EMEYEYPUXY3RG&Signature=Bl7CXJbMb5DauC%2F73txCwFmvmtQ%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEN%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIBX4nw9I7%2FE2cnnEUIetj2sA4ns0TNw1l%2BO1OOLZfxFwAiEArNarMK34dtzboqG2SKZeYvuBwjsUSYzTZLOQ3K4d6iEq%2FAQIqP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARABGgw2OTk3NTMzMDk3MDUiDI1wfE2hfGHTrvvi6CrQBKN12ZTqB8zQ0zDvJ4EZ3Ps4dxa%2FMmhQ96si37AySg1%2F1i58bHljQHJiBX3WZQo9qUKArEP8AdejWa%2Bp6Y0Z0a1oKQOALzZIYvbG6ul4%2F3hmWu5idh1zQKET%2FD2QIBOa7M5%2F6DkAgnEiE8Q4wgbdEHjwrWGA2cMeCbRgqoEU%2BMqWlJiAm1MBKPX%2FcOi6HPNYHQiNXE0zBplXdGD508KRO0P2FvJG3FNznfg1jADggZ4oHMeO8RNP4ong3O%2FjhXhRstdZwb%2B2eHW96RTVQ0td0KwK7lhJrXyJH6sSiscoJfe2yM7ParVnVuHLHX5Ke90taBc9Fa3eFymDhlq%2F0H6PHevoNsfycgU%2FL4kSLLdxq8YWneWmNqJZjzcnqt0cNI5gjq6MdJDCW%2FzIfKN8vbbPvdIPeuJMq668e8ty4BH3wZg6GDz3qxurwU52GkZmfE1gJ8ggxonguKIr%2FvNQ7DES3Bzs1qgyFvfYvOvX9B7R6IJSnasw7aV%2BbqPBdENe9IrH7t01MlZzDsuMv9FLgXJ0gPvG91RTNDYr%2FaGspvWIWjJbs4itJiVQ%2BfBhPiAg4qAzSFiXh3Nqez6xHKZoIn8vgKzK4D%2B4vGpuF8CpmFW3khp2bNtmisha%2FKTttq9gsPRmgn7I1wdO85xgCVeQ6X96isTgfe6xVDFRK8og1VAkX%2FivAYBxyZIlXTwBFv52K60RH1WAcQtIjA17Y0vs%2FvtaBhBlCbflXu6yH3rlcq6b4hOR2gl2WCPW0CrfMR%2FcnebrJxxRVlTgu661YDdUuk5ZLNYw34qx0wY6mAERhkItzMNcrQN46La%2FeeW8vba8K%2BVuQFm9M3Jf4anFENeu%2Fdzz%2FaeWsj%2FOAwK2m27meuKDMnXAwQex619YB6FFUr%2BBdazkGC4aKjXbGtvFqDC3iZ3%2FzHFo6dTXDh%2BLzP1KJMi%2FJ8yLNenFessLD664y0hvT6Fus7rL7TAQNVjRRoccHHp3iGSAv%2FpSUmhFsyOll6fIfGtvhQ%3D%3D&Expires=1785484082)

## Updated master handoff
Here is the revised version with your expert’s changes incorporated and the “preserve backend wording” line softened as requested. I’ve kept it strict, implementation-oriented, and UI-safe.

# MRI Frontend V1 — Master Handoff Document

**Frontend Contract Version:** v1.0  
**Compatible with:** Backend Contract v1.0, MRI Product Bible v1.0

## 1. Product intent
MRI is an investment decision platform, not a screener, charting app, or chatbot. The V1 frontend exists to help the user answer three questions quickly: what should I do this week, why is that the recommendation, and what happened previously. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/8781877/8a49a5ca-586b-4e35-b74c-71008008acec/MRI-Product-Bible.md?AWSAccessKeyId=ASIA2F3EMEYEYPUXY3RG&Signature=Bl7CXJbMb5DauC%2F73txCwFmvmtQ%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEN%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIBX4nw9I7%2FE2cnnEUIetj2sA4ns0TNw1l%2BO1OOLZfxFwAiEArNarMK34dtzboqG2SKZeYvuBwjsUSYzTZLOQ3K4d6iEq%2FAQIqP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARABGgw2OTk3NTMzMDk3MDUiDI1wfE2hfGHTrvvi6CrQBKN12ZTqB8zQ0zDvJ4EZ3Ps4dxa%2FMmhQ96si37AySg1%2F1i58bHljQHJiBX3WZQo9qUKArEP8AdejWa%2Bp6Y0Z0a1oKQOALzZIYvbG6ul4%2F3hmWu5idh1zQKET%2FD2QIBOa7M5%2F6DkAgnEiE8Q4wgbdEHjwrWGA2cMeCbRgqoEU%2BMqWlJiAm1MBKPX%2FcOi6HPNYHQiNXE0zBplXdGD508KRO0P2FvJG3FNznfg1jADggZ4oHMeO8RNP4ong3O%2FjhXhRstdZwb%2B2eHW96RTVQ0td0KwK7lhJrXyJH6sSiscoJfe2yM7ParVnVuHLHX5Ke90taBc9Fa3eFymDhlq%2F0H6PHevoNsfycgU%2FL4kSLLdxq8YWneWmNqJZjzcnqt0cNI5gjq6MdJDCW%2FzIfKN8vbbPvdIPeuJMq668e8ty4BH3wZg6GDz3qxurwU52GkZmfE1gJ8ggxonguKIr%2FvNQ7DES3Bzs1qgyFvfYvOvX9B7R6IJSnasw7aV%2BbqPBdENe9IrH7t01MlZzDsuMv9FLgXJ0gPvG91RTNDYr%2FaGspvWIWjJbs4itJiVQ%2BfBhPiAg4qAzSFiXh3Nqez6xHKZoIn8vgKzK4D%2B4vGpuF8CpmFW3khp2bNtmisha%2FKTttq9gsPRmgn7I1wdO85xgCVeQ6X96isTgfe6xVDFRK8og1VAkX%2FivAYBxyZIlXTwBFv52K60RH1WAcQtIjA17Y0vs%2FvtaBhBlCbflXu6yH3rlcq6b4hOR2gl2WCPW0CrfMR%2FcnebrJxxRVlTgu661YDdUuk5ZLNYw34qx0wY6mAERhkItzMNcrQN46La%2FeeW8vba8K%2BVuQFm9M3Jf4anFENeu%2Fdzz%2FaeWsj%2FOAwK2m27meuKDMnXAwQex619YB6FFUr%2BBdazkGC4aKjXbGtvFqDC3iZ3%2FzHFo6dTXDh%2BLzP1KJMi%2FJ8yLNenFessLD664y0hvT6Fus7rL7TAQNVjRRoccHHp3iGSAv%2FpSUmhFsyOll6fIfGtvhQ%3D%3D&Expires=1785484082)

### North Star
Every UI decision must reduce the time required for an investor to understand and act on an investment decision.

## 2. Assumptions
- Backend APIs already exist.
- Backend responses conform to the documented schema.
- Authentication is already implemented.
- Decision logic is backend-owned.
- Desktop browser is the primary target.

## 3. V1 scope
### In scope
- Dashboard.
- Stock Decision page.
- Decision Ledger.

### Out of scope
- Charts.
- AI chat.
- Mobile-specific work.
- Watchlists.
- Alerts.
- Notifications.
- Portfolio analytics.
- Sector views.
- Compare stocks.
- User settings.
- Manual trade execution.
- Custom filters.
- Any client-side scoring or investment logic.

## 4. V1 design rules
- Desktop only.
- Light theme only.
- No animations beyond subtle transitions.
- No charts in V1.
- No drag and drop.
- No resizing panels.
- No floating windows.
- No configurable layouts.

## 5. Navigation
Use only these navigation items:
- Dashboard.
- Decision Ledger.

If a distinct Portfolio view is not materially different from the Dashboard, do not ship it in V1. Fold portfolio summary into the Dashboard to reduce navigation and cognitive load. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/8781877/8a49a5ca-586b-4e35-b74c-71008008acec/MRI-Product-Bible.md?AWSAccessKeyId=ASIA2F3EMEYEYPUXY3RG&Signature=Bl7CXJbMb5DauC%2F73txCwFmvmtQ%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEN%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIBX4nw9I7%2FE2cnnEUIetj2sA4ns0TNw1l%2BO1OOLZfxFwAiEArNarMK34dtzboqG2SKZeYvuBwjsUSYzTZLOQ3K4d6iEq%2FAQIqP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARABGgw2OTk3NTMzMDk3MDUiDI1wfE2hfGHTrvvi6CrQBKN12ZTqB8zQ0zDvJ4EZ3Ps4dxa%2FMmhQ96si37AySg1%2F1i58bHljQHJiBX3WZQo9qUKArEP8AdejWa%2Bp6Y0Z0a1oKQOALzZIYvbG6ul4%2F3hmWu5idh1zQKET%2FD2QIBOa7M5%2F6DkAgnEiE8Q4wgbdEHjwrWGA2cMeCbRgqoEU%2BMqWlJiAm1MBKPX%2FcOi6HPNYHQiNXE0zBplXdGD508KRO0P2FvJG3FNznfg1jADggZ4oHMeO8RNP4ong3O%2FjhXhRstdZwb%2B2eHW96RTVQ0td0KwK7lhJrXyJH6sSiscoJfe2yM7ParVnVuHLHX5Ke90taBc9Fa3eFymDhlq%2F0H6PHevoNsfycgU%2FL4kSLLdxq8YWneWmNqJZjzcnqt0cNI5gjq6MdJDCW%2FzIfKN8vbbPvdIPeuJMq668e8ty4BH3wZg6GDz3qxurwU52GkZmfE1gJ8ggxonguKIr%2FvNQ7DES3Bzs1qgyFvfYvOvX9B7R6IJSnasw7aV%2BbqPBdENe9IrH7t01MlZzDsuMv9FLgXJ0gPvG91RTNDYr%2FaGspvWIWjJbs4itJiVQ%2BfBhPiAg4qAzSFiXh3Nqez6xHKZoIn8vgKzK4D%2B4vGpuF8CpmFW3khp2bNtmisha%2FKTttq9gsPRmgn7I1wdO85xgCVeQ6X96isTgfe6xVDFRK8og1VAkX%2FivAYBxyZIlXTwBFv52K60RH1WAcQtIjA17Y0vs%2FvtaBhBlCbflXu6yH3rlcq6b4hOR2gl2WCPW0CrfMR%2FcnebrJxxRVlTgu661YDdUuk5ZLNYw34qx0wY6mAERhkItzMNcrQN46La%2FeeW8vba8K%2BVuQFm9M3Jf4anFENeu%2Fdzz%2FaeWsj%2FOAwK2m27meuKDMnXAwQex619YB6FFUr%2BBdazkGC4aKjXbGtvFqDC3iZ3%2FzHFo6dTXDh%2BLzP1KJMi%2FJ8yLNenFessLD664y0hvT6Fus7rL7TAQNVjRRoccHHp3iGSAv%2FpSUmhFsyOll6fIfGtvhQ%3D%3D&Expires=1785484082)

## 6. Component ownership

### Backend owns
- Decision logic.
- Scoring.
- Confidence.
- Business reasoning.
- Evidence.
- Priority.
- Sorting.
- Calculations.

### Frontend owns
- Layout.
- Rendering.
- Navigation.
- Expand/collapse.
- Loading states.
- Error states.
- Accessibility.
- Responsive layout.

## 7. Frontend NEVER
The frontend must never:
- Calculate MRI.
- Calculate MOSI.
- Calculate confidence.
- Infer recommendations.
- Sort differently from backend.
- Hide backend fields.
- Merge backend fields.
- Rewrite backend wording.
- Reclassify decision semantics.
- Substitute its own business logic.
- Invent missing data.

## 8. Screen requirements

### 8.1 Dashboard
#### Purpose
Answer: **What should I do this week?**

#### Must display
- Portfolio Summary.
- Portfolio Health.
- Market Regime.
- Cash Available.
- Weekly Decisions sorted by priority.

#### Must do
- Clicking a recommendation opens the associated Stock Decision page.
- Show a clear empty state if no recommendations exist.
- Show loading, error, and partial-data states cleanly.

### 8.2 Stock Decision
#### Purpose
Answer: **Why did MRI make this recommendation?**

#### Layout order
1. Recommendation.
2. Why.
3. Rules.
4. Evidence.

#### Must display
- Action.
- Confidence.
- One-line summary.
- Primary reason.
- Supporting reasons.
- All evaluated rules.
- All supporting evidence.

#### Must do
- Expand/collapse each section independently.
- Default-open Recommendation first.
- Preserve backend meaning; minor UI formatting is permitted, but business terminology and recommendation semantics must remain unchanged.
- Show `No data available` where a section exists but has no entries.

### 8.3 Decision Ledger
#### Purpose
Answer: **What decisions were made before, and what happened?**

#### Must display a read-only table with:
- Date.
- Stock.
- Decision.
- Executed.
- Outcome.

#### Must do
- Clicking a row opens the associated Stock Decision page.
- Show empty, loading, error, and partial states cleanly.

## 9. Data contract
The frontend must render only backend-supported fields and must not infer, calculate, or rewrite decision logic.

### Dashboard schema
- portfolioSummary
- portfolioHealth
- marketRegime
- cashAvailable
- weeklyDecisions

### Stock Decision schema
- recommendation
- why
- rules
- evidence

### Decision Ledger schema
- date
- stock
- decision
- executed
- outcome
- decisionId

## 10. Backend-to-UI mapping

### Dashboard
| UI | Backend |
|---|---|
| Portfolio Summary | portfolioSummary |
| Portfolio Health | portfolioHealth |
| Market Regime | marketRegime |
| Cash Available | cashAvailable |
| Weekly Decisions | weeklyDecisions |

### Weekly decision item
| UI | Backend |
|---|---|
| Stock name | stock |
| Action | action |
| Priority | priority |
| Confidence | confidence |
| Summary | summary |
| Decision link | decisionId |

### Stock Decision
| UI | Backend |
|---|---|
| Action | recommendation.action |
| Confidence | recommendation.confidence |
| One-line summary | recommendation.summary |
| Primary reason | why.primaryReason |
| Supporting reasons | why.supportingReasons |
| Rules | rules[] |
| Evidence | evidence[] |

### Rules item
| UI | Backend |
|---|---|
| Rule name | name |
| Rule status | status |
| Rule detail | detail |

### Evidence item
| UI | Backend |
|---|---|
| Evidence label | label |
| Evidence value | value |
| Evidence status/type | status / type |

### Decision Ledger
| UI | Backend |
|---|---|
| Date | date |
| Stock | stock |
| Decision | decision |
| Executed | executed |
| Outcome | outcome |
| Row link | decisionId |

## 11. Sample payloads

### Dashboard
```json
{
  "portfolioSummary": {
    "name": "Main Portfolio",
    "totalValue": "₹12,45,000",
    "pnl": "+12.4%"
  },
  "portfolioHealth": {
    "status": "Healthy",
    "notes": "Exposure within limits"
  },
  "marketRegime": {
    "status": "Positive",
    "notes": "Weekly trend supportive"
  },
  "cashAvailable": "₹85,000",
  "weeklyDecisions": [
    {
      "decisionId": "dec_001",
      "stock": "Neuland Labs",
      "action": "ADD",
      "priority": 1,
      "confidence": 91,
      "summary": "Weekly trend remains intact."
    }
  ]
}
```

### Stock Decision
```json
{
  "decisionId": "dec_001",
  "stock": "Neuland Labs",
  "recommendation": {
    "action": "ADD",
    "confidence": 91,
    "summary": "Weekly trend remains intact."
  },
  "why": {
    "primaryReason": "Weekly trend intact",
    "supportingReasons": [
      "Higher highs maintained",
      "No hard rules triggered"
    ]
  },
  "rules": [
    {
      "name": "Weekly Structure",
      "status": "PASS",
      "detail": "Higher-high / higher-low sequence intact"
    }
  ],
  "evidence": [
    {
      "label": "30W EMA",
      "value": "PASS",
      "status": "PASS"
    }
  ]
}
```

### Decision Ledger
```json
{
  "items": [
    {
      "decisionId": "dec_001",
      "date": "2026-07-26",
      "stock": "Neuland Labs",
      "decision": "ADD",
      "executed": true,
      "outcome": "Open"
    }
  ]
}
```

## 12. State handling
### Loading
Show skeletons or neutral placeholders.

### Empty
- Dashboard: `No weekly recommendations are available right now.`
- Stock Decision: `No decision details are available for this stock.`
- Decision Ledger: `No past decisions found.`

### Error
- Dashboard: `Unable to load your weekly MRI data. Try again.`
- Stock Decision: `Unable to load decision details. Try again.`
- Decision Ledger: `Unable to load decision history. Try again.`

### Partial data
Render whatever is available and mark missing sections as unavailable.

## 13. Performance expectations
- Page loads under 2 seconds under normal conditions.
- Navigation should feel instant.
- No layout shift after content loads.
- Skeletons should exist for all async data.

## 14. UX rules
- Weekly decisions are sorted by backend priority ascending.
- Each decision row is clickable.
- Each ledger row is clickable.
- Collapsible sections on Stock Decision open independently.
- Confidence should not be invented if missing.
- If a section has no entries, show `No data available`.
- Render only what the backend provides.

## 15. Routing map
- `/dashboard` → Dashboard.
- `/decision/:decisionId` → Stock Decision.
- `/ledger` → Decision Ledger.

## 16. Component inventory
### Shared
- App shell.
- Top navigation.
- Section header.
- Skeleton loader.
- Error banner.
- Empty state panel.

### Dashboard
- Portfolio summary card.
- Portfolio health card.
- Market regime card.
- Cash available card.
- Weekly decision item.

### Stock Decision
- Recommendation card.
- Accordion section.
- Rule row.
- Evidence row.

### Ledger
- Table.
- Table row.
- Status chip.

## 17. Definition of done
A feature is complete only when:
- It builds successfully.
- There are no TypeScript errors.
- There are no lint errors.
- All acceptance criteria pass.
- It is responsive on supported desktop widths.
- No placeholder text remains.
- No mocked data remains.
- Backend contract is unchanged.

## 18. Acceptance criteria
The build is complete only when:
1. Dashboard renders successfully.
2. Weekly recommendations render from backend data.
3. Clicking a recommendation opens the right Stock Decision.
4. Stock Decision shows recommendation, why, rules, and evidence.
5. Decision Ledger shows historical decisions.
6. Clicking a ledger row opens the right Stock Decision.
7. Loading, empty, error, and partial states work correctly.
8. No extra features are present.
9. The UI is usable without developer explanation.

## 19. Final implementation rule
If a behavior, label, or field is not specified in this document, the team must treat it as out of scope until explicitly approved. That is the safest way to protect clarity, reduce scope creep, and keep MRI focused on decision quality. [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/8781877/8a49a5ca-586b-4e35-b74c-71008008acec/MRI-Product-Bible.md?AWSAccessKeyId=ASIA2F3EMEYEYPUXY3RG&Signature=Bl7CXJbMb5DauC%2F73txCwFmvmtQ%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEN%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIBX4nw9I7%2FE2cnnEUIetj2sA4ns0TNw1l%2BO1OOLZfxFwAiEArNarMK34dtzboqG2SKZeYvuBwjsUSYzTZLOQ3K4d6iEq%2FAQIqP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARABGgw2OTk3NTMzMDk3MDUiDI1wfE2hfGHTrvvi6CrQBKN12ZTqB8zQ0zDvJ4EZ3Ps4dxa%2FMmhQ96si37AySg1%2F1i58bHljQHJiBX3WZQo9qUKArEP8AdejWa%2Bp6Y0Z0a1oKQOALzZIYvbG6ul4%2F3hmWu5idh1zQKET%2FD2QIBOa7M5%2F6DkAgnEiE8Q4wgbdEHjwrWGA2cMeCbRgqoEU%2BMqWlJiAm1MBKPX%2FcOi6HPNYHQiNXE0zBplXdGD508KRO0P2FvJG3FNznfg1jADggZ4oHMeO8RNP4ong3O%2FjhXhRstdZwb%2B2eHW96RTVQ0td0KwK7lhJrXyJH6sSiscoJfe2yM7ParVnVuHLHX5Ke90taBc9Fa3eFymDhlq%2F0H6PHevoNsfycgU%2FL4kSLLdxq8YWneWmNqJZjzcnqt0cNI5gjq6MdJDCW%2FzIfKN8vbbPvdIPeuJMq668e8ty4BH3wZg6GDz3qxurwU52GkZmfE1gJ8ggxonguKIr%2FvNQ7DES3Bzs1qgyFvfYvOvX9B7R6IJSnasw7aV%2BbqPBdENe9IrH7t01MlZzDsuMv9FLgXJ0gPvG91RTNDYr%2FaGspvWIWjJbs4itJiVQ%2BfBhPiAg4qAzSFiXh3Nqez6xHKZoIn8vgKzK4D%2B4vGpuF8CpmFW3khp2bNtmisha%2FKTttq9gsPRmgn7I1wdO85xgCVeQ6X96isTgfe6xVDFRK8og1VAkX%2FivAYBxyZIlXTwBFv52K60RH1WAcQtIjA17Y0vs%2FvtaBhBlCbflXu6yH3rlcq6b4hOR2gl2WCPW0CrfMR%2FcnebrJxxRVlTgu661YDdUuk5ZLNYw34qx0wY6mAERhkItzMNcrQN46La%2FeeW8vba8K%2BVuQFm9M3Jf4anFENeu%2Fdzz%2FaeWsj%2FOAwK2m27meuKDMnXAwQex619YB6FFUr%2BBdazkGC4aKjXbGtvFqDC3iZ3%2FzHFo6dTXDh%2BLzP1KJMi%2FJ8yLNenFessLD664y0hvT6Fus7rL7TAQNVjRRoccHHp3iGSAv%2FpSUmhFsyOll6fIfGtvhQ%3D%3D&Expires=1785484082)

If you want, I can now produce this as a **clean repo-ready Markdown file** with a title page and a one-line change log section.
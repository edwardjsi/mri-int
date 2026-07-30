import os

with open('Decisions.md', 'a') as f:
    f.write('\n\n## Decision 108 — MRI Frontend V1 Scope and Constraints\nDate: 2026-07-30\nDecision: Build a hyper-minimal frontend strictly focused on the weekly review and decision ledger, removing charts, AI chat, and standalone portfolio views. A right-side panel will be used for progressive disclosure of XAI.\nReason: To optimize for decision-making speed (under 10 mins for 20 stocks) and validate the core Decision Engine and Explainability without UI overhead.\nStatus: FINAL.\n')

with open('Progress.md', 'a') as f:
    f.write('\n\n### Updated Next Smallest Step\n- Implement the MRI Frontend V1 based on the `30 July 26 MRI Frontend V1.md` PRD. Start by updating the `WeeklyReviewDashboard.tsx` to include the Decision Ledger navigation, remove unsupported views, and implement the right-side Stock Decision Panel to parse and display the `ExplanationNode` tree.\n')

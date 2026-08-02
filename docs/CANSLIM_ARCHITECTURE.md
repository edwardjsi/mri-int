# CANSLIM Architecture

1. **Consume, never calculate.**
   The CANSLIM model must act purely as a consumer of existing primitives (MRI database, technical indicators, fundamental scores). It must never re-calculate technical logic locally.

2. **Models produce verdicts, not rankings.**
   The CANSLIM model is responsible for evaluating rules and producing individual component verdicts (C, A, N, S, L, I, M). A centralized Portfolio Ranking Engine handles the final ranking.

3. **All qualitative decisions originate from the Company Knowledge Service via the Knowledge Rule Engine.**
   Qualitative components (Catalyst, Institutional) must be backed by canonical observations and exact string evidence extracted by the AI, processed deterministically by rule engines.

# CAI Canonical Terms & Glossary

This document serves as the immutable source of truth for terminology across the entire CAI architecture. To prevent terminology drift and ensure alignment across engineering and product teams, these definitions must be used consistently in all code, documentation, and user interfaces.

| Term | Canonical Meaning |
|------|-------------------|
| **Threshold** | A mathematically computed price boundary. Never contains business logic. |
| **Decision** | The final output of the Resolution Engine. |
| **Evidence** | An objective observation produced by Rule Engines. |
| **Rule** | A deterministic function that produces evidence. |
| **Policy** | Portfolio-level governance that constrains decisions. |
| **Structure** | The current technical integrity of the trend. |
| **Opportunity** | Conditions under which additional capital may be deployed. |
| **Risk** | Conditions under which capital protection becomes increasingly important. |
| **Observation** | An objective fact detected from data before any interpretation. |
| **Inference** | A conclusion drawn from one or more pieces of evidence. |
| **Decision Engine** | The orchestration layer that combines evidence, thresholds, rules, and policies into a single decision. |
| **Decision State** | The current lifecycle state of a position (`ADD`, `HOLD`, `ALERT`, `STRUCTURE`, `QUIT`). |
| **MOSI** | Management, Operations, Strategy, and Industry. The fundamental intelligence engine evaluating structured and unstructured corporate data. |
| **Resolution** | The process of evaluating mathematical thresholds against current market state to determine an actionable recommendation. |
| **Ladder** | The presentation and organizational framework (opportunity vs risk flow) of a single stock's technical state. |

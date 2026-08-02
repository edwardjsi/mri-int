# Lead AI Engineer Instructions

> **Every commit should make at least one investment decision more accurate, more explainable, or faster for the end user.**

You are the lead AI engineer for this project.

Before writing or modifying any code:

**Read:**
- `Readme.md` and `.llm-context.md` (Project Context)
- `docs/PLUMBING_AND_ORCHESTRATION.md` (System Map & Data Flow)
- `Decisions.md` (Decision Log)
- `Sessions.md` (Session Summary)
- `Progress.md` and `Tasks.md` (Milestones and Tasks)
- `AGENTS.md` (This file)

**Summarize:**
- Current system architecture
- What has been completed
- Known constraints
- Open tasks

**Confirm:**
- Which milestone we are currently implementing (based on `Progress.md` and `Tasks.md`)

**Then:**
- Propose the next smallest logical implementation step
- Explain reasoning
- Only then generate code

**Rules:**
- Do not redesign architecture unless explicitly asked.
- Follow conventions defined in `AGENTS.md`.
- Keep changes incremental and testable.
- Update `Sessions.md` and `Progress.md` at the end.
- Push the day's work to git at the end of the day.

---

## 📌 90-DAY MANDATE
> **For the next 90 days, success is measured by better knowledge, better rules, and better calibration—not by new architecture.**
> **Every merge should make GRANULES a better investment dossier than it was yesterday.**

### 🛑 CAI Platform Rules (Post-M1 Freeze)

**Rule 1 — No new infrastructure without approval**
The platform interfaces are frozen. If someone proposes a new service, API, engine, document, or architectural layer, the default answer is **No** unless there is a demonstrable implementation blocker.

**Rule 2 — Every commit must improve one of four workstreams**
Every PR should belong to exactly one category:
1. **Knowledge** (better extraction)
2. **Rules** (new deterministic rules)
3. **Calibration** (measure and improve rule quality)
4. **Models** (CANSLIM, Minervini, etc.)

**Rule 3 — Every rule needs evidence**
No rule should ever return a naked PASS or FAIL. Every rule must trace back to an Observation, which traces back to a Fact, which traces back to an exact string Quote. If you can't explain it, you shouldn't ship it.

**Rule 4 — Knowledge compounds, architecture doesn't**
Your competitive advantage is 500 companies with excellent knowledge, 200 calibrated rules, and years of deterministic evidence. It is not another endpoint or abstraction.

**Rule 5 — Every feature must improve one company**
Whenever you build something new, ask: *"If I open GRANULES immediately after this merge, what is better?"* (More facts? Better entities? Better rules?) If the answer is "nothing," it isn't delivering value yet.

**Rule 6 — Delete temporary code aggressively**
Delete mock JSON, fake repositories, stub rules, and placeholder code. Every sprint should remove more scaffolding than it adds.

**Rule 7 — The One-Day Rule**
A competent investment analyst should be able to review every change from a single day's work in under 30 minutes. Limit PR size to specific, testable, measurable improvements (e.g., "Today we improved the Business section of Granules").

**Rule 8 — Mandatory UX and Benefit Documentation**
Every PR must include a "Before" screenshot, an "After" screenshot, and a one-sentence "Investor Benefit". Example: "Investor Benefit: I can immediately identify whether a holding is fundamentally strong, technically improving, and well understood without opening another screen."

### Definition of Value

A change creates value if it improves at least one of the following:

✓ Knowledge coverage
✓ Rule accuracy
✓ Calibration metrics
✓ Model performance
✓ Explainability
✓ User experience
✓ Runtime performance
✓ Reliability

If none of these measurably improve, reconsider the change.

---

## ⛔ CRITICAL: RDS Protection Rules (Decision 026/027)

**Context:** On 2026-03-04, `terraform destroy -target=module.vpc` cascaded and destroyed the RDS database, causing total data loss (1.7M rows, 3 client accounts, all signals/portfolio data).

**Rules — NEVER VIOLATE:**
1. **NEVER run `terraform destroy` without first removing RDS from state** — Use `terraform state rm` on all `module.rds.*` resources before any destroy operation.
2. **NEVER suggest `terraform destroy -target=module.vpc`** — RDS depends on VPC; Terraform will cascade-destroy it.
3. **NEVER modify these RDS protections in `modules/rds/main.tf`:**
   - `deletion_protection = true`
   - `skip_final_snapshot = false`
   - `prevent_destroy = true` (lifecycle)
4. **ALWAYS use `scripts/mri_safe_teardown.sh`** for daily teardown, NEVER `terraform destroy` directly.
5. **ALWAYS use `scripts/mri_teardown.sh`** ONLY for stopping AWS resources (RDS + bastion), NOT for destroying infrastructure.

See `Decisions.md` → Decision 026 (incident) and Decision 027 (safeguards) for full details.

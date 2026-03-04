# Lead AI Engineer Instructions

You are the lead AI engineer for this project.

Before writing or modifying any code:

**Read:**
- `Readme.md` and `.llm-context.md` (Project Context)
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

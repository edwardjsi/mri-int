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

# Prepared kit (disclosure file)

This kit was prepared before the competition. It contains **setup only, no project code**:
agent instructions, a scoring rubric, skills, templates and a key smoke test.
Copy it into the platform-created team repo after the official start and list it in
README section "Prior code and sources".

| File | Purpose |
|---|---|
| `AGENTS.md`, `CLAUDE.md` | Shared instructions for Codex and Claude Code |
| `docs/RUBRIC.md`, `docs/TASK.md`, `docs/PLAN.md`, `docs/WORKFLOW.md`, `docs/COMMANDS.md` | Rubric, task template, plan, Claude + Codex workflow, command cheat sheet |
| `.claude/skills/*` | Skills: task-intake, review-diff, checkpoint, rubric-check, readme-writer, clean-clone-check, ask-codex |
| `.claude/agents/*` | Subagents: qa-tester, rules-auditor |
| `.claude/settings.json` | Denies reading `.env` |
| `README.md`, `.env.example`, `.gitignore`, `Makefile` | Templates |
| `scripts/smoke.py` | Checks that API keys and endpoints work |
| `scripts/push-advice.sh` | Read-only: says whether a commit/push to GitHub is recommended now |
| `docs/HACKATHON_RULES.md`, `.hackathon-rules.conf` | Rules summary with clause numbers; settings (competition times, team repo) |
| `scripts/rules-check.sh`, `scripts/install-hooks.sh`, `scripts/hooks/*` | Warn before commits and pushes when the rules are at risk; block only on secrets or a real `.env` |
| `.vscode/*` | Editor settings |

Before the event, ask the organizers whether generic setup files like these are allowed if disclosed.

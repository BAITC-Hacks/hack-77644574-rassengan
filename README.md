# hack-77644574-rassengan
Hackathon team repository for rassengan

> {Project name}: {one-line description}

> Team: {names}. Task: {task}. Built at HackAlem AI, 23 Sep 2026.

## What it does
{The task, the main scenario, who it helps.}

## Architecture
{Components and data flow (a small diagram helps). Which model does what and why.}

## Tech and data
- Stack: {language, framework}
- Providers and models: {Claude / NVIDIA / OpenAI, model IDs}
- Built with OpenAI Codex {and Claude Code}
- Data: {sources}

## Prior code and sources
- **Prepared kit** (added on the competition day, setup only, no project code): agent instructions, skills, templates, rule-check scripts and `scripts/smoke.py`. Full list and purpose in `KIT.md`:
  - `AGENTS.md`, `CLAUDE.md`
  - `docs/RUBRIC.md`, `docs/TASK.md`, `docs/PLAN.md`, `docs/WORKFLOW.md`, `docs/COMMANDS.md`
  - `.claude/skills/*`
  - `.claude/settings.json`
  - `README.md`, `.env.example`, `.gitignore`, `Makefile`
  - `scripts/smoke.py`
  - `scripts/push-advice.sh`
  - `docs/HACKATHON_RULES.md`, `.hackathon-rules.conf`
  - `scripts/rules-check.sh`, `scripts/install-hooks.sh`, `scripts/hooks/*`
  - `.vscode/*`
- {other libraries, models, datasets, templates and their licenses}

## System requirements
- OS: {macOS / Linux / Windows}; {Python 3.x / Node x / Docker}; {RAM, GPU if any}

## Dependencies
- Listed in {requirements.txt / package.json / pyproject.toml}, versions pinned. Installed by `make setup`.

## Install and run
```bash
git clone {repo url} && cd {repo}
cp .env.example .env   # then fill in the values (see Configuration)
make setup             # installs dependencies
make run
```

## Access for judges (no personal accounts needed)
{Demo / test credentials, or how to run in mock/offline mode without any personal account or subscription.}

## Configuration
| Variable | Purpose | Example |
|---|---|---|
| ANTHROPIC_API_KEY | | |

## Verify the main scenario
1. {step}
2. Expected: {result}

## Team and contributions
- {name} (GitHub {handle}): {what they built}

## Tests
`make test`

## Known limitations
- {honest list}

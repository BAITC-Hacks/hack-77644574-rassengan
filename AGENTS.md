# Project rules for coding agents (Codex, Claude Code)

> Shared source of truth. `CLAUDE.md` imports this file. Fill the {placeholders} at the start of the competition.

## Goal
- Task: Smart contractor matching (#79-lite). One sentence: an event client gives city, date, event type, category and budget and gets up to 3 contractors, each with a specific, fact-based explanation.
- Main scenario: request -> hard filters with counted rejection reasons -> deterministic ranking -> top 3 -> fact-based explanation (LLM with template fallback) -> one of 3 explicit outcomes. Everything else is secondary.
- Mandatory task conditions live in `docs/TASK.md`. Read it before any change.
- Scoring lives in `docs/RUBRIC.md`: the task spec's scoring table (technical round) plus Demo Day criteria. Work is judged against it.

## Stack and layout
- Language/stack: Python 3.9+, FastAPI, uvicorn, pytest, one static HTML page. Do not add frameworks without asking.
- All LLM calls go through one module (`llm.py` or equivalent). Never import a vendor SDK elsewhere.
- Providers come from env vars (see `.env.example`). Never hard-code keys or model IDs in code.

## Commands
- Run: `make run`
- Test: `make test`
- Smoke test of API keys: `python scripts/smoke.py`

## Rules
- Before finishing any change: run `make test` and `make run`. Fix failures; never skip or delete tests to get green.
- Never write secrets into any file. `.env` is git-ignored; keep `.env.example` current.
- No mocked or hard-coded outputs presented as real. If something is stubbed, list it in README "Known limitations".
- Small commits, message format `type: what changed` (feat, fix, test, docs, chore).
- Validate all LLM output against a schema; handle timeouts, retries and invalid input.
- Keep `README.md` in sync with what actually works: install, run, verify, limits.
- Do not touch files outside the task's scope. Ask before large refactors or new dependencies.

## Working together (Codex <-> Claude Code)
- Claude Code can delegate a build step to Codex with the `ask-codex` skill (`codex exec`).
- Codex can ask Claude Code for a review or second opinion by running `claude -p "<prompt>"` in the shell (read-only prompts, e.g. "Review git diff against docs/TASK.md. Do not edit files."). The MCP server `claude` (`claude mcp serve`) gives Codex Claude's file and shell tools only; its `Agent` tool has no agent types in this mode, so do not use it.
- Only one agent edits files at a time. Commit between handoffs so each diff is reviewable.

## Push advice (applies to every agent)
Progress that is not on GitHub is not safe and not visible to the organizers. Proactively recommend pushing.
- Run `scripts/push-advice.sh` at the end of every finished step. If it says `RECOMMEND PUSH NOW` or `RECOMMEND COMMIT NOW`, tell the user in one line: "Recommend pushing now: {reason}".
- Also recommend a push (without waiting for the script) when: the main scenario or a mandatory condition works for the first time; a step passes `make test` and `make run`; before a risky refactor or dependency change; before switching agents, laptops or teammates; at each hourly checkpoint; before the feature freeze and before the final deadline.
- Recommend a commit first if there are uncommitted working changes.
- Never push without the user's OK in this session. Ask once, plainly ("Push to origin/main? yes/no"). If the user says "push automatically at checkpoints", follow that for the rest of the session only.
- Before proposing a push, check the diff for secrets; if any are found, recommend fixing that first and do not push.
- Do not push broken states to a shared branch unless the user asks; say what is broken.

## Rules compliance (applies to every agent)
The team must not break the hackathon rules (summary and clause numbers: `docs/HACKATHON_RULES.md`).
- Before every commit or push you propose or make, run `scripts/rules-check.sh` (git hooks may also run it). Tell the user each `[ERROR]` and `[WARN]` in plain words, with the fix.
- An `[ERROR]` (secret or real `.env`): stop, fix it first, never bypass with `--no-verify`.
- A `[WARN]`: tell the user before committing or pushing and let them decide; do not silently ignore it.
- Never use `--no-verify`, force-push, delete remote branches, or rewrite pushed history unless the user explicitly asks; say why it matters (visible development history is required).
- Manual rules no tool can check (presence on site, personal participant number, one person one team, hourly results, disclosure of reused code, no fake results) are listed in `docs/HACKATHON_RULES.md`; raise them when relevant.
- If a request would break a rule (for example copying a large pre-built project into the repo, or hard-coding results), say so and propose a compliant alternative.

## Competition rules that affect you
- Coding window: 13:00–18:00 Asia/Almaty, 23 Sep 2026. **The repo state at 18:00 is final** (rule 5.4.13); aim to push the final version by 17:55.
- Only work in this repo; keep visible commit history. A confirmed result pushed every hour (14:00, 15:00, 16:00, 17:00, 18:00), or disqualification (rules 5.4.8, 5.9.2).
- Core task functionality must be written during the competition; the kit is setup only (rules 5.4.4.2, 5.4.5).
- Disclose reused code, libraries, templates, datasets and open models in README "Prior code and sources" (rule 5.4.4).
- **Hard gate:** if experts cannot run the final version by following the README, the team is out; no explanations accepted (rule 5.4.16). The README must have: purpose, architecture, technologies, system requirements, dependencies, install, environment variables, run, how to verify the main scenario (rule 5.4.15).
- **No personal accounts needed** to verify key features: provide demo credentials or a mock/offline mode (rule 5.6.6).
- An AI judge reads the repo, docs, structure and tests: keep them clean and real (rules 4.2–4.4).
- Results are licensed to the organizer without limits (rule 6.1): never add employer code, private data or unlicensed material.

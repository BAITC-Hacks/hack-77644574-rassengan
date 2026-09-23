@AGENTS.md

# Claude Code specifics

Shared rules are in `AGENTS.md` above. This file only adds what is specific to Claude Code.

## Role in this project
- Default role: planner, reviewer and verifier. Codex is the main builder (the hackathon requires Codex use).
- When asked to implement, keep changes small and end with `make test` and `make run` results.
- When asked to review, check the diff against `docs/TASK.md` and `docs/RUBRIC.md` and report concrete problems by file and line, most serious first. Do not rewrite code during a review unless asked.

## Handoff files (read before starting, update before stopping)
- `docs/TASK.md`: mandatory conditions of the chosen task.
- `docs/RUBRIC.md`: scoring criteria and points.
- `docs/PLAN.md`: current plan, what is done, what is next, blockers. Keep it short.

## Skills available in `.claude/skills/`
- `task-intake`: turn `docs/TASK.md` into a scope, a plan and the first Codex prompt.
- `review-diff`: read-only review of the latest changes against the task and rubric.
- `checkpoint`: hourly verify, update `docs/PLAN.md`, produce a status line.
- `rubric-check`: score the current repo against the rubric and list the cheapest gains.
- `readme-writer`: write or refresh `README.md` from what the repo actually does.
- `clean-clone-check`: prove the project runs from a fresh clone before the freeze.
- `ask-codex`: delegate one build step to Codex (`codex exec`), then review its diff.

## Subagents in `.claude/agents/`
- `qa-tester`: runs setup/test/run and the main scenario like a judge, tries bad input, may add tests only.
- `rules-auditor`: read-only audit against the regulations, the hard gates and the rubric.

## Push advice
Follow "Push advice" in `AGENTS.md`. At the end of each task run `scripts/push-advice.sh`; when it says RECOMMEND PUSH/COMMIT, or one of the listed situations applies, say so in one line with the reason, then wait for the user's yes before pushing.

## Rules compliance
Follow "Rules compliance" in `AGENTS.md`: run `scripts/rules-check.sh` before proposing any commit or push, report every ERROR/WARN with the fix, and read `docs/HACKATHON_RULES.md` when a rule question comes up.

## Behaviour
- Never read or print `.env`. Refer to variable names only.
- If something is unclear in the task, say what you assume instead of guessing silently.
- Be honest about what does not work yet; do not claim untested behaviour.

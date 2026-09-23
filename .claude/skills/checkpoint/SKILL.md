---
name: checkpoint
description: Do the hourly checkpoint: verify the project runs, make sure progress is committed, update docs/PLAN.md and produce a one-line status for the team chat. Use every hour of the competition.
---

# Hourly checkpoint

The rules require a confirmed intermediate result every hour and visible commit history, so this must be quick and honest.

1. Run `git status` and `git log -5 --format='%h %ad %s' --date=iso`. Report uncommitted work and the time of the last commit.
2. Run `make test` and `make run` (or the documented commands). Record the real outcome.
3. Compare with the plan in `docs/PLAN.md`: which goal for this hour is done, partly done or missed.
4. Update the hourly log row in `docs/PLAN.md` (result, commit hash) and the Now / Next / Blockers sections. Be truthful about partial results.
5. Run `scripts/push-advice.sh`. If work is uncommitted and it runs, tell the user exactly what to commit (proposed message in `type: what changed` form). A checkpoint is always a "push is recommended" moment: say so with the reason, and ask "Push to origin? yes/no". Do not commit or push yourself without a yes.
6. Run `scripts/rules-check.sh` (manual mode) and report every ERROR/WARN in plain words with the fix; include the hourly-evidence result. Nothing is pushed while an ERROR (secret, real `.env`) exists.
7. Output:
   - one-line status for the team chat, e.g. "H2: main scenario works for X, tests pass, next: error handling";
   - risks for the next hour;
   - the next step as a ready-to-paste prompt for Codex.

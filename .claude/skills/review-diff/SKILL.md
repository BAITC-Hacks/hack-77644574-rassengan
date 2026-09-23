---
name: review-diff
description: Read-only review of the latest changes (usually what Codex just built) against docs/TASK.md and docs/RUBRIC.md. Use after each build step, before committing or moving to the next step.
---

# Review diff

This is a read-only review. Do not edit files.

1. Read `docs/TASK.md`, `docs/RUBRIC.md` and `docs/PLAN.md` to know what the current step should deliver.
2. Look at what changed: `git status`, `git diff` (uncommitted) and `git log -5` with `git diff HEAD~1` if the work is already committed.
3. Run `make test` and `make run` (or the documented commands). Report actual results.
4. Check the change for:
   - does it deliver the current step from `docs/PLAN.md`, and satisfy the mandatory conditions it touches;
   - bugs, unhandled bad input, missing timeouts or error handling;
   - fake, hard-coded or canned results presented as real;
   - vendor SDK calls outside the LLM layer, hard-coded keys or model IDs, secrets in the diff;
   - unrequested extras, scope creep, new dependencies;
   - README or `.env.example` that no longer match the code.
5. Report findings by file and line, most serious first, each with a one-line fix suggestion. Separate "must fix now" from "can wait".
6. Run `scripts/rules-check.sh` and include its ERRORs and WARNs in the findings (with the rule numbers); a rule ERROR always means "fix first". Then run `scripts/push-advice.sh`. If the verdict is "OK to commit" and the step works, recommend committing and pushing (with the reason) and ask before pushing.
7. Finish with a verdict: OK to commit and continue / fix first, and the text of a ready-to-paste prompt for Codex containing the fixes.

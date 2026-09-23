---
name: ask-codex
description: Delegate one build step to OpenAI Codex non-interactively (codex exec) and then review what it changed. Use when the user says "ask codex", "let codex build", "delegate to codex", or when a PLAN.md step is ready to implement.
---

# Ask Codex

Codex builds, Claude plans and reviews (see `docs/WORKFLOW.md`). Visible Codex use matters at this hackathon.

1. Make sure the step is concrete: take it from `docs/PLAN.md` or ask the user. One step per call.
2. Check `git status --short`. If there are uncommitted changes, tell the user and suggest committing first so Codex's diff is easy to review.
3. Write the prompt: goal, files in scope, acceptance check (`make test` / exact command), and "follow AGENTS.md". Keep it self-contained; Codex does not see this conversation.
4. Run from the repo root (it can take several minutes; use a long timeout or run in background):
   ```bash
   codex exec -C "$(git rev-parse --show-toplevel)" -s workspace-write \
     -o /tmp/codex-last.txt "<prompt>"
   ```
   Read-only questions: use `-s read-only`. Never pass flags that skip the sandbox or approvals.
5. Read `/tmp/codex-last.txt` and `git diff --stat` / `git diff`. Review against `docs/TASK.md` and `docs/RUBRIC.md`; run `make test`.
6. Report to the user: what Codex changed, test results, problems by file and line. Then follow "Push advice" in `AGENTS.md` (run `scripts/rules-check.sh`, recommend commit, wait for a yes). Suggest the commit message mention Codex, e.g. `feat: <what> (built with Codex)`.

If `codex` is not found: it is a wrapper at `~/.local/bin/codex` for `/Applications/ChatGPT.app/Contents/Resources/codex`.

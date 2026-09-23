# Using Claude Code and Codex together

Simple rule: **Codex builds, Claude Code plans, reviews and verifies. Git is the handoff.**
The hackathon requires Codex use, so Codex does the visible building; Claude adds a second pair of eyes.
Check exact commands on the day (`codex --help`, `claude --help`); tools change.

## 1. One shared source of truth
Both agents read the same files, so they never disagree:
- `AGENTS.md` (Codex reads it; `CLAUDE.md` imports it for Claude Code)
- `docs/TASK.md` (mandatory conditions), `docs/RUBRIC.md` (scoring), `docs/PLAN.md` (status)
- The same commands for both: `make run`, `make test`

## 2. Who does what
| Job | Lead | Why |
|---|---|---|
| Turn the task into a scope and plan | Claude Code | Good at reading requirements and spotting gaps |
| Write the code, tests, scaffolding | Codex | Required by the event; fast at implementation from a clear spec |
| Review the diff against the task and rubric | Claude Code | Independent check finds what the builder missed |
| Fix failing tests or runs | Whichever is already in that file | Avoid context switching |
| Draft and verify the README | Claude Code (`readme-writer`) | Hard gate: no run from README = out (rule 5.4.16) |
| Pre-freeze verification | Claude Code (`clean-clone-check`, `rubric-check`) | Experts deploy from a clean clone; 18:00 version is final |

## 3. The loop (repeat every hour)
1. **Plan (Claude, 5 min).** "Read docs/TASK.md, docs/RUBRIC.md, docs/PLAN.md. Propose the next hour's goal and 3-5 steps. Update PLAN.md." Human approves.
2. **Build (Codex, 30-40 min).** Give it one step at a time from PLAN.md. Ask for a plan first, then the change. Commit after every working step.
3. **Review (Claude, 5-10 min).** "Review `git diff main` against TASK.md and RUBRIC.md. List concrete problems by file and line, most serious first. Don't edit."
4. **Fix (Codex).** Paste the review findings; Codex fixes; run `make test`.
5. **Checkpoint (everyone, 2 min).** Push, update the hourly log in `docs/PLAN.md`, post a one-line status in the team chat.

## 4. Avoid stepping on each other
- **One writer per file at a time.** Do not run both agents editing the same files.
- If both must write at once, give each its own branch or git worktree (`git worktree add ../work-claude -b claude-work`), then merge often. Keep it small; merge conflicts cost more than they save in a 5-hour event.
- Reviews are read-only: tell Claude Code "do not edit" or run it in plan/read-only mode.
- Commit before switching agents so the other one sees the latest state.

## 5. Useful prompts
**Scope (Claude):**
> Read docs/TASK.md and docs/RUBRIC.md. Write the smallest main scenario that satisfies every mandatory condition and scores well on the rubric. List what we will NOT do. Update docs/PLAN.md.

**Build step (Codex):**
> Read AGENTS.md and docs/PLAN.md. Implement only step {N}. Run make test and make run. Show the diff summary and how to verify it.

**Review (Claude):**
> Review the last commits against docs/TASK.md and docs/RUBRIC.md. Run make test. Report: bugs, missing mandatory conditions, unhandled bad input, fake or hard-coded results, secrets. Do not edit files.

**Second opinion (either direction):**
> Here is the other agent's proposal: {paste}. Find what is wrong or risky with it before I accept it.

**Rubric check (Claude):** `/rubric-check`
**README (Claude):** `/readme-writer`
**Before freeze (Claude):** `/clean-clone-check`

## 6. What goes wrong
- Two agents making different design choices: settle it in `docs/PLAN.md` and tell both to follow it.
- Long, vague prompts: one small step per prompt.
- Trusting green output: the agent said "done" but nobody ran it. Always run `make run` yourself once per hour.
- Agent commits a secret: `.env` is git-ignored and denied in `.claude/settings.json`; still check `git diff` before every push.
- Burning API credits on the agents' own work: the organizers' keys are meant for the product; check whether they may also power the coding agents. Use your own subscriptions for Claude Code and Codex if unsure.
- Rate limits: keep one agent as fallback; the other can carry on.

## 7. Disclosure
State in the README that the project was built with Codex and Claude Code, and list the prepared kit files (see `KIT.md`).

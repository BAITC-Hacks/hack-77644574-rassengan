# What to run, and when

A cheat sheet so nobody has to remember. Slash commands go in the **Claude Code** terminal.
Prompts marked *Codex* go in the **Codex** panel. Shell lines go in a normal terminal.

## Before the event (today / tomorrow)
| Do | How |
|---|---|
| Check your keys work | `pip install anthropic openai python-dotenv` then `python scripts/smoke.py` |
| Try the whole loop on a made-up task | Fill `docs/TASK.md` with a small fake task and run steps 1–6 below |
| Ask organizers the open questions | see the prep brief, "Questions for the organizers" |
| Install and log in to both agents | `claude` and `codex` in a terminal; confirm each answers |

## At the venue, before the start
1. `cp .env.example .env` and fill in the organizers' keys and endpoints (never commit `.env`).
2. `python scripts/smoke.py` — every provider you plan to use must say OK.
3. Install the kit into the platform-created team repo. In Claude Code, from any folder, type:
   `/install-kit <path or GitHub URL of the team repo>`
   It shows a dry run, copies without overwriting anything, adds the disclosure line to the README, then asks before committing and separately before pushing.
   By hand instead: `~/hackathon-kit/scripts/install-kit.sh <team-repo> --dry-run`, then again without `--dry-run`.

## Start of the competition
| Step | Command / prompt | Who |
|---|---|---|
| 1. Paste the task | Open `docs/TASK.md`, paste the organizers' text and mandatory conditions verbatim | You |
| 2. Scope and plan | `/task-intake` | Claude Code |
| 3. First build step | Paste the ready-made prompt that `/task-intake` prints | Codex |

## The hourly loop
| Step | Command / prompt | Who |
|---|---|---|
| Build | *Codex:* `Read AGENTS.md and docs/PLAN.md. Implement only step {N}. Run make test and make run. Show the diff summary.` | Codex |
| Run it yourself | `make run` and `make test` | You |
| Review | `/review-diff` | Claude Code |
| Fix | Paste the fix prompt from the review into Codex | Codex |
| Commit and push | `git add -A && git commit -m "feat: {what}" && git push` | You |
| Checkpoint | `/checkpoint` then post the one-line status in the team chat | Claude Code |

## Any time
| Need | Command |
|---|---|
| See where we stand against the scoring | `/rubric-check` |
| Draft or refresh the README | `/readme-writer` |
| Prove it runs from a clean clone | `/clean-clone-check` |
| Second opinion on a proposal | Ask: `Here is Codex's proposal: {paste}. What is wrong or risky with it?` |
| Are we breaking any hackathon rule? | `scripts/rules-check.sh` (runs automatically before commit and push once hooks are installed with `scripts/install-hooks.sh`; explanations in `docs/HACKATHON_RULES.md`) |
| Fill in competition times and team repo for the checks | edit `.hackathon-rules.conf` |
| Should we push now? | `scripts/push-advice.sh` (agents run it too and will tell you "Recommend pushing now: {reason}") |
| Undo a bad change | `git diff` to see, `git checkout -- {file}` to revert one file |

## Last 45 minutes (feature freeze already happened)
1. `/readme-writer`
2. `/rubric-check` — fix only cheap, high-point items
3. `/clean-clone-check` — must pass on a clean copy, ideally on another laptop
4. Check for secrets: `git log -p | grep -iE "api[_-]?key|secret|token" | head`
5. Final push before the platform locks the repo.
6. Rehearse the 3-minute demo once.

## Command reference
| Command | What it does | Changes files? |
|---|---|---|
| `/task-intake` | Turns TASK.md into scope, plan and the first Codex prompt | Yes: PLAN.md, TASK.md §6, AGENTS.md placeholders |
| `/review-diff` | Reviews the latest changes against task and rubric | No |
| `/checkpoint` | Hourly verify, log and status line | Yes: PLAN.md only |
| `/install-kit` | Global command: installs the kit into a repo (no overwrite, asks before commit and push) | Yes: adds kit files to the target repo |
| `/rubric-check` | Scores the repo against the rubric | No |
| `/readme-writer` | Writes README from the real state of the repo | Yes: README.md |
| `/clean-clone-check` | Fresh-clone run and secret scan | No |

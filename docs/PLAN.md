# Plan and status (keep short; update every hour)

Case: smart contractor matching (#79-lite). Team: Askhat (lead, main dev) + Nurdaulet (QA, acceptance, defense).

## Hourly log
| Hour | Goal | Result | Commits |
|---|---|---|---|
| H1 13:00–14:00 | Case choice, task files, scaffold, data loader, filters | Pipeline on the official CSV, 3 outcomes, 22 tests | 0ff7c7f, 0dbc324 |
| H2 14:00–15:00 | Explainable ranking, trace, DoD tests, LLM explainer with checker | Score breakdown, trace, LLM + template fallback, README v1; independent acceptance review | df173a9, e875f99, 24248cd, a4b4153 (Nurdaulet) |
| H3 15:00–16:00 | Calendar bounds (from review), Windows setup, free-text mode, explanation quality | 422 outside 23.09–31.12.2026, /parse, ranking reasons in explanations, 186 tests; pitch + re-review | 187382d, 5b44e64, 37b7eb4, 9f06fc8, d2a21b6, d5510dd (Nurdaulet) |
| H4 16:00–17:00 | Checks and fixes: clean clone (macOS + Windows), rules audit, demo rehearsal | | |
| 17:00–18:00 | 17:30 feature freeze, final README, final clean-clone check, final push by 17:55 | | |

## Split
- Askhat (with Codex + Claude Code): `app/`, `web/`, `tests/`, `README.md`.
- Nurdaulet (with Codex): `docs/ACCEPTANCE_REVIEW.md`, `docs/PITCH.md`, acceptance tests, Windows clean-clone check.

## Now
- Clean-clone check on macOS: passed at d2a21b6 (make setup, 186 tests, 5 README scenarios without a key).
- Waiting: Windows clean-clone result from Nurdaulet.

## Blockers / open questions
- None.

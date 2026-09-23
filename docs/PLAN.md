# Plan and status (keep short; update every hour)

Case: smart contractor matching (#79-lite). Team: Askhat (lead, main dev) + Nurdaulet (QA, acceptance, defense).

## Hourly log
| Hour | Goal | Result | Commits |
|---|---|---|---|
| H1 13:00–14:00 | Case choice, task files, scaffold, data loader, filters | Pipeline on the official CSV, 3 outcomes, 22 tests | 0ff7c7f, 0dbc324 |
| H2 14:00–15:00 | Explainable ranking, trace, DoD tests, LLM explainer with checker | Score breakdown, trace, LLM + template fallback, README v1; independent acceptance review | df173a9, e875f99, 24248cd, a4b4153 (Nurdaulet) |
| H3 15:00–16:00 | Calendar bounds (from review), Windows setup, free-text mode, explanation quality | 422 outside 23.09–31.12.2026, /parse, ranking reasons in explanations, 186 tests; pitch + re-review | 187382d, 5b44e64, 37b7eb4, 9f06fc8, d2a21b6, d5510dd (Nurdaulet) |
| H4 16:00–17:00 | Checks and fixes: clean clone (macOS + Windows), rules audit, redesign | README/`/parse` fixes, `make demo` + `make eval`, live report, redesign (Claude Design), Windows CP1251 fix, distinct explanations (DoD2 bug from review); Nurdaulet: Windows + live AI acceptance, pitch | f888ba9, 66d5e6d, 2a45fc7, c01517a, 8ca19e5, 71eb98c, d7f3ff6; 49758c2 (Nurdaulet) |
| H5 17:00–18:00 | Last review fixes, freeze, final checks | No unsupported comparisons on tied scores; review fixes (event-relevant distinct facts, late-answer deadline). Code freeze 17:03. Final clean clone of 4c256b9: setup, 210 tests, make demo 28/28, API scenarios, 0 secrets in history; live eval 22/23 AI; browser flows with live AI | cd242e9, 4c256b9, this commit |

## Split
- Askhat (with Codex + Claude Code): `app/`, `web/`, `tests/`, `README.md`.
- Nurdaulet (with Codex): `docs/ACCEPTANCE_REVIEW.md`, `docs/PITCH.md`, acceptance tests, Windows clean-clone check.

## Now
- Final: code frozen at 4c256b9 (17:03); verified by clean clone and live AI. No further commits after the final docs push.

## Blockers / open questions
- None.

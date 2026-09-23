# Plan and status (keep short; update every hour)

Case: smart contractor matching (#79-lite). Team: Lead (main dev) + Junior.

## Hourly log
| Hour | Goal | Result | Commit |
|---|---|---|---|
| H1 13:00–14:00 | Task files, scaffold (FastAPI + static page + pytest), data loader, filters | | |
| H2 14:00–15:00 | Scoring + ranking + 3 outcomes + "why fewer than 3"; tests for mandatory 1–6 | | |
| H3 15:00–16:00 | Explanations: fact-based template + LLM rewrite with fallback; DoD2/DoD4 tests | | |
| H4 16:00–17:00 | UI polish, demo queries, synthetic profiles marked, error handling. 17:30 feature freeze | | |
| 17:00–18:00 | README final, clean-clone check, rules-auditor, demo script. Final push by 17:55 | | |

## Split
- Lead (with Codex + Claude): `app/` pipeline (load, filter, score, explain), API, tests.
- Junior: `data/` (dataset in place, check fields), `demo/queries.md` (dense / rare / empty / two-dates queries with expected results), `web/index.html` form, README "Verify the main scenario". Commit own work under own GitHub account.

## Now
- Working on: scaffold
- Owner: Lead

## Blockers / open questions
- Dataset file `hackathon-dataset-anonymized.jsonl`: download from the case page into `data/`.

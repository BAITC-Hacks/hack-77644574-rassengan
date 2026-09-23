---
name: rubric-check
description: Score the current repository against the hackathon rubric (docs/RUBRIC.md) and list the cheapest ways to gain points. Use when asked to check progress, review before an hourly checkpoint, or before the freeze.
---

# Rubric check

1. Read `docs/TASK.md`, `docs/RUBRIC.md` and `docs/PLAN.md`.
2. Inspect the repo as a judge would: README, run command, `.env.example`, tests, source layout, git log.
3. Actually run `make test` and `make run` (or the documented run command). Report real results, never assumed ones.
4. Score each criterion of the task spec's scoring table in `docs/RUBRIC.md` (if it is still `{…}`, say so and use the fallback list there), giving points out of the maximum, with one line of evidence (file path or command output) for each.
5. Check the mandatory task conditions from `docs/TASK.md` one by one: met / partly / missing.
6. Check the hard gates in `docs/HACKATHON_RULES.md` (runs from README alone, all required README sections, no personal accounts needed) and the disqualification risks in `docs/RUBRIC.md`, including: secrets in the repo or history, recent commits (one per hour), undisclosed reused code.
7. Finish with a short list of the cheapest improvements, ordered by points gained per minute. Do not change code unless asked.

Output format: a table of criteria with score and evidence, then "Mandatory conditions", "Risks", "Next 3 actions".

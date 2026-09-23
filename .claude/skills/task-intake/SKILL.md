---
name: task-intake
description: Turn the filled-in docs/TASK.md into a minimal main scenario, a "not doing" list and an hour-by-hour plan in docs/PLAN.md. Use at the start of the competition, right after the task is pasted into docs/TASK.md.
---

# Task intake

Goal: the smallest project that satisfies every mandatory condition and scores well on `docs/RUBRIC.md`.

1. Read `docs/TASK.md`, `docs/RUBRIC.md`, `AGENTS.md` and `docs/PLAN.md`.
2. If `docs/TASK.md` still contains `{…}` placeholders in sections 1-4, list exactly what is missing and stop; do not guess.
3. Restate each mandatory condition as one testable sentence ("Given X, the system does Y"). Flag any that are ambiguous and propose an assumption, and a question for the organizers.
4. Propose the main scenario in one sentence (input → result) and confirm it covers every mandatory condition. Name anything it cannot cover.
5. Write a "Not doing" list of tempting extras that would not add points.
6. Suggest the stack only if `AGENTS.md` has none; prefer the simplest thing the team already knows.
7. Update `docs/PLAN.md`: fill the hourly table with concrete goals for this task (skeleton with live LLM call by H1, main scenario by H2, and so on), and a numbered list of build steps small enough to give Codex one at a time (each step: what to build, how to verify).
8. Write the decisions back into `docs/TASK.md` section 6 and fill the placeholders in `AGENTS.md` (goal, stack, main scenario).
9. Do not write application code. End with the first build step, formatted as a ready-to-paste prompt for Codex.

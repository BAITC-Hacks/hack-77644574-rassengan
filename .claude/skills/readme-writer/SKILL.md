---
name: readme-writer
description: Write or refresh README.md from what the repository actually does, so a human or AI judge can install, run and verify it. Use when asked to update the README or near the end of the competition.
---

# README writer

The README replaces a presentation and is judged on content, not looks. It is read by both people and an AI judge.

1. Read `docs/TASK.md`, the source code, `Makefile`, `.env.example`, tests and `KIT.md`.
2. Keep the existing section structure of `README.md`: What it does, Architecture, Tech and data, Prior code and sources, System requirements, Dependencies, Install and run, Access for judges, Configuration, Verify the main scenario, Team and contributions, Tests, Known limitations. Rule 5.4.15 requires: purpose, architecture, technologies, installation, run, dependencies, environment parameters, how to verify the main scenario. If experts cannot deploy from it, the team is out (rule 5.4.16).
3. Describe only what really works. Verify every command by running it. If a command fails, fix the README or report it; never leave unverified instructions.
4. Configuration table must list every environment variable used in code, with a purpose and an example value (no real keys).
5. "Verify the main scenario" needs exact steps and the expected output so a judge can check it in minutes.
6. "Prior code and sources": list reused code, libraries, open models, datasets, templates and the prepared kit files.
7. "Known limitations": be honest about stubs, unfinished parts and assumptions.
8. "Access for judges": key features must be verifiable without the team's personal accounts or subscriptions (rule 5.6.6). Give demo/test credentials or a mock/offline mode.
9. State that the project was built with OpenAI Codex and Claude Code where that is true.
10. Keep it factual and compact. No marketing language.

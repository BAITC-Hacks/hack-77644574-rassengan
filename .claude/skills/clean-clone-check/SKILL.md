---
name: clean-clone-check
description: Prove the project runs from a fresh clone using only the README, and that no secrets are committed. Use before the feature freeze and before the final push.
---

# Clean-clone check

Experts run the project in a clean environment from the README alone. If it fails, the team is out and no explanations are accepted (rule 5.4.16). Run this by 17:30 at the latest.

1. Make sure everything intended is committed (`git status` must be clean). Report anything untracked or ignored that the project needs.
2. Clone the repository into a temporary directory outside the working tree (use the scratchpad or `mktemp -d`), from the local repo path.
3. Follow the README's install and run steps literally, in order, in that fresh directory. Use `.env.example` as the starting point; if real keys are needed, take them from the environment without printing them.
4. Check that nothing needs a personal account or subscription (rule 5.6.6). Run the "Verify the main scenario" steps and `make test`. Record pass/fail and any missing dependency, file or variable.
5. Scan the tracked files and git history for secrets: strings that look like API keys, `.env` files, tokens. Report file and commit, never the secret itself.
6. Report: what worked, what failed, the exact README fix or missing file for each failure, and whether it is safe to freeze.
7. Do not modify the project unless asked; report first.

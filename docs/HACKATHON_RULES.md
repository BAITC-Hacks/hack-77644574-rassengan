# Hackathon rules: what is checked automatically and what the team must check

Source: HackAlem AI regulations ("Положение") on edu.astanahub.com, version updated 22 Sep 2026. Clauses are
cited as "rule N.N". The organizers may add instructions through official channels (rules 3.2, 3.4, 5.4.2):
update this file and `.hackathon-rules.conf` when they do. This is a working summary, not legal text: when in
doubt, read the original and ask the organizers (team@baitc.org, Telegram chat).

## The day (23 Sep 2026, Astana time, UTC+5)
| Time | What |
|---|---|
| 09:00–12:00 | Check-in: personal participant number (from the Telegram bot), full name, phone |
| 12:00–13:00 | Opening ceremony |
| **13:00** | **Competition starts** (rule 5.3.1). Repo history and hourly rules apply from here |
| 14:00, 15:00, 16:00, 17:00, 18:00 | Hourly checkpoints: confirmed progress each hour (rule 5.4.8) |
| **18:00** | **Official end. Repo content at 18:00 is the final version** (rule 5.4.13) |
| 24–28 Sep | Technical review (AI judge + technical experts) → finalists |
| 29 Sep | Demo Day (finalists present to the jury) |
| 1 Oct | Awards at AI & Digital Bridge 2026 |

## How the warnings work
- `scripts/rules-check.sh` runs **automatically before every commit and push** once hooks are installed
  (`scripts/install-hooks.sh`, offered by `/install-kit`). It also runs when Claude Code or Codex commit for you.
- **ERROR** blocks the commit or push (secrets, real `.env` files). **WARN** prints a message and lets you continue.
- Run it any time: `scripts/rules-check.sh`. Stricter (warnings also block): `RULES_STRICT=1 scripts/rules-check.sh`.
- Bypass knowingly with `git commit --no-verify` / `git push --no-verify`. Say why in the team chat.
- Agents (Codex, Claude Code) run it before committing/pushing and tell you the warnings in plain words.

## Checked automatically

| Level | Check | Rule | Triggers when | What to do |
|---|---|---|---|---|
| ERROR | Real `.env` file | 5.6.6, 6.1.7 (and safety) | a `.env` or `.env.*` file (not `.env.example`) is staged or in the pushed commits | Remove it from git, keep it in `.gitignore` |
| ERROR | Key-shaped secrets | safety | a line matches a known key format (Anthropic, OpenAI-style, NVIDIA, AWS, GitHub, Slack, private key) | Remove it, use an env var, rotate the key. Output shows file and line, never the value |
| WARN | Credential-looking line | safety | `api_key = "…24+ chars…"` style assignment | Use an environment variable |
| WARN | Not the official repo | 5.4.9, 5.4.11, 5.9.2 | no `origin` remote, or its URL does not contain `REPO_REMOTE_PATTERN` | Main development must be in the platform-created repo |
| WARN | Work before the start | 5.4.4.2, 5.4.5 | competition start is set, it has not begun, and non-setup files are committed | Only setup files before 13:00 |
| WARN | Work after the end | 5.4.13, 5.4.14 | competition end is set and has passed | The 18:00 version is final; later changes are not judged |
| WARN | Hourly evidence | 5.4.8, 5.9.2 | (manual run) last commit is over `HOURLY_MAX_MIN` minutes old during the competition | Commit and push a working result |
| WARN | Large drop of code | 5.4.4, 5.4.5, 5.4.6 | one commit or push adds 1500+ lines or 40+ files outside setup files | Be ready to show where it came from; disclose reused code |
| WARN | Tracked dependencies | 5.4.15, 5.6.3 | `node_modules`, `.venv`, `__pycache__` are tracked | Untrack; list dependencies in a manifest |
| WARN | Personal ID file | 5.2.3, 5.2.6 | a filename looks like a QR code / participant ID image | Never publish your personal participant number |
| WARN | README not judge-ready | 5.4.15, 5.6.4 | README missing, still has `{…}` placeholders, or lacks a required section | Run `/readme-writer` |
| WARN | Kit not disclosed | 5.4.4 | `KIT.md` exists but README has no "Prior code" section | Add the section |
| WARN | `.env.example` missing | 5.4.15, 5.6.4 | file not present | Add it with every variable, no real values |
| WARN | Task file empty | (agents need it) | `docs/TASK.md` still has `{…}` | Paste the task and its technical spec |
| WARN | History rewrite | 5.4.11, 5.9.2 | a push is a force push / non-fast-forward, or deletes a remote branch | Keep visible history |

## HARD GATES: fail one and the project is out

1. **It must run from the README alone** (rules 5.4.15, 5.4.16, 5.6.3–5.6.5). If the experts cannot start the
   final version by following the README, the team is excluded from selection. **No explanations or fixes are
   accepted afterwards.** Run `/clean-clone-check` before 17:30.
2. **The README must contain** (rules 5.4.15, 5.6.4): description and purpose; architecture; technologies;
   system requirements; dependencies; installation steps; environment variables / parameters; run steps;
   how to verify the main scenario. It must let an expert understand and deploy it alone.
3. **No personal accounts needed to verify** (rule 5.6.6). Key features must be testable without the team's
   personal accounts, personal subscriptions or closed accounts. For external services/APIs, provide demo access,
   test credentials, or a documented mock/offline mode.
4. **The 18:00 version is final** (rules 5.4.13, 5.4.14). Everything, including Demo Day, is judged on it.

## Disqualification grounds (rule 5.9.2)
- No confirmed intermediate result for any reporting hour (see 5.4.8: code/repo changes, feature, prototype, design,
  architecture diagram, tuned model, tests, prepared data).
- A participant is absent without permission (emergencies excepted, notify at once).
- No check-in or other attendance procedures.
- Main development outside the platform-created GitHub repo, or no verifiable development history in it.
- False registration data; one person in several teams.
- A project wholly or mainly made by third parties without disclosure.
- Interfering with platforms, equipment, networks, attendance systems or other teams' projects; malicious code,
  unauthorized access or attacks.
- Aggressive, offensive, discriminatory or unethical behavior; pressure, bribery or improper influence on experts,
  judges, partners or the organizer.
- Breaking venue rules, safety, public order or Kazakhstan law.
- Refusing lawful organizational requests or the documents needed to confirm results or receive prizes.
- Anything else that breaks fairness, good faith or the reliability of results.
Disqualification can happen without warning when the breach is serious or deliberate (rule 5.9.3).

## Must be checked by people (no tool can see these)

**Presence and identity**
- Every member is on site from check-in until the official end. No development off-site (rule 5.1.7).
- Leaving needs the organizer's prior permission; total absence max 60 minutes (rule 5.1.7.1). Emergencies
  (health, family, safety) are exempt, but notify the organizer at once (rule 5.1.7.2).
- Check in yourself with your **own** participant number; never pass it on (rules 5.2.3, 5.2.6).
- One person, one team, one project (rule 5.1.6). Team changes after 20 Sep need the organizer's consent (5.2.7).
- Bring a laptop, charger, software, accounts and a LAN adapter that fits it (rule 5.2.8).

**How the work is done**
- All main development in the platform-created repo, which is the single working repo, with real history from
  13:00 (rules 5.4.9, 5.4.11). Other online services, clouds and APIs are fine while you are on site (5.4.12.1).
- Every hour a real, confirmed intermediate result (rule 5.4.8).
- The core functionality for the task must be built during the competition. Prepared tools, own libraries,
  templates and infrastructure are allowed only if they are not the product or its core (rules 5.4.4.2, 5.4.5).
- Disclose all third-party material: open-source code, libraries, models, datasets, templates, the prepared kit
  (rules 5.4.4, 5.4.4.1, 5.4.6). Follow each license.
- One project for one task only (rule 5.4.1.1).
- Experts may check repos, demos, code, architecture, functionality, **use of required tools**, truthfulness of
  claims, git history, file metadata and **each member's contribution** (rules 4.1, 5.4.7). Every member should
  commit under their own GitHub account and be able to explain their part.
- AI tools and agents of any kind are allowed (rule 5.4.12). Codex is optional per the rules unless the task
  requires it; the landing page says it is required. OpenAI is the main sponsor: use Codex visibly and say so in
  the README.
- No canned or hard-coded results presented as real.

**Conduct**
- Do not interfere with platforms, equipment, networks, or other teams' projects; no malicious code or
  unauthorized access. No pressure or bribery. Follow venue rules and Kazakhstan law (rule 5.9.2).

**Good to know**
- Technical criteria and points come from **the chosen task's technical spec**, published before 13:00
  (rules 5.5.1–5.5.3). An AI judge pre-scores repos (rules 1.17, 4.2–4.4); it reads the repository,
  documentation, project structure, tests and supporting materials.
- No appeals: technical-selection and jury results are final; only arithmetic/technical errors are corrected
  (rule 5.10). A reworked project after the deadline is not reviewed.
- **IP (rule 6.1):** the organizer gets a free, unlimited, perpetual right to use, modify, publish and transfer
  the results to third parties. Do not put employer code, private data or anything you cannot license into the repo.
  You guarantee no infringement, no malicious code and correct licensing (rule 6.1.7).
- Photo and video filming and publication of your name, team and project are consented to (rule 6.2).
- 10 main prize places, single overall ranking, no per-task quotas (rule 5.8.1). Prizes go to the captain under a
  contract; taxes may be withheld; the team splits internally (rules 5.8.4–5.8.7).
- Food: 4 sandwich packs and 3 L water per person; own food must be non-perishable, no strong smell (rule 6.3.5).

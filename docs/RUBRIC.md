# Scoring rubric

Source: HackAlem AI regulations on edu.astanahub.com (version of 22 Sep 2026), rules 5.5–5.7.

## How projects are judged (pipeline)
1. **Primary check, pass/fail** (rule 5.6.1): hackathon conditions met, materials complete, **it runs from the
   README**. If it does not run from the README, the team is out, with no explanations accepted (rule 5.4.16).
2. **AI judge pre-scoring** (rules 1.17, 4.2–4.4): analyzes the repository, documentation, project structure,
   tests and supporting materials, and scores each criterion. Make the repo easy for a machine to read.
3. **Technical experts** (rules 5.5, 5.6): score by **the chosen task's technical spec** → finalists.
   Results across the 10 tasks are normalized onto one scale (rule 5.5.4).
4. **Demo Day jury** (rule 5.7): finalists only, table below. The jury's collective decision overrides the sum.

## Technical round: criteria come from the TASK SPEC
The regulations no longer contain a fixed technical rubric. **Paste the chosen task's scoring table here at
13:00 and treat it as priority #1.** Only criteria published before 13:00 apply (rule 5.5.3).

| Criterion (from task spec) | Pts | What is checked | Our evidence |
|---|---|---|---|
| {…} | {…} | {…} | {…} |

Until the task spec is known, assume experts and the AI judge also look at (rules 4.1, 5.4.15, 5.6):
- mandatory task requirements met; main scenario works end to end;
- claimed features really exist in code; clear structure; no canned or fake results;
- README with all required sections (see `docs/HACKATHON_RULES.md`, hard gates);
- reproducible from a clean clone; dependencies pinned; `.env.example`; no personal accounts needed (rule 5.6.6);
- tests and handling of invalid input;
- use of required tools (Codex visibly used) and each member's real contribution in the git history.

## Demo Day (finalists only), 100 points
| Criterion | Pts | What the jury looks at |
|---|---|---|
| Value of the solution | 25 | Real, understandable problem; significant, obvious benefit for the target audience |
| Result and quality | 20 | The prototype really delivers the claimed scenario; integrity and quality of the user result (no code re-check) |
| Innovation | 15 | New or non-standard approach, different from obvious alternatives, own advantage |
| Growth and scaling potential | 20 | Use after the hackathon: new users, organizations, industries, scenarios |
| Presentation, demo and Q&A | 20 | Clear problem, solution and advantages; convincing demo; good answers |

Demo Day judges the **18:00 version** only (rule 5.4.14). Every member should be able to explain their own part (rule 4.6).

## Disqualification risks (rule 5.9.2), keep clear of all of these
- No confirmed intermediate result for any reporting hour.
- Main development outside the platform-created GitHub repo, or no verifiable development history.
- Undisclosed third-party or reused work; a pre-existing product submitted as new.
- Leaving the venue without permission; passing your participant number to someone else.
- Secrets, malicious code, or interfering with others' systems.

#!/usr/bin/env bash
# rules-check.sh — warns when the repo is drifting from the HackAlem AI rules. Read-only.
# Usage: scripts/rules-check.sh [--stage commit|push|manual] [--refs-from-stdin]
# Exit code 1 only when an ERROR is found (secrets, .env) and RULES_BLOCK is not 0.
# RULES_STRICT=1 also fails on warnings (useful near the freeze). Rules: docs/HACKATHON_RULES.md
set -uo pipefail

STAGE="manual"; REFS=0
while [ $# -gt 0 ]; do
  case "$1" in
    --stage) STAGE="${2:-manual}"; shift 2 ;;
    --refs-from-stdin) REFS=1; shift ;;
    -h|--help) sed -n '2,5p' "$0"; exit 0 ;;
    *) shift ;;
  esac
done

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "rules-check: not a git repository"; exit 0; }
cd "$(git rev-parse --show-toplevel)"

# ---- config (edit .hackathon-rules.conf) -----------------------------------
COMPETITION_START=""; COMPETITION_END=""; REPO_REMOTE_PATTERN=""
HOURLY_MAX_MIN=60; LARGE_COMMIT_LINES=1500; LARGE_COMMIT_FILES=40
# shellcheck disable=SC1091
[ -f .hackathon-rules.conf ] && . ./.hackathon-rules.conf

if [ -t 1 ]; then R=$'\033[31m'; Y=$'\033[33m'; G=$'\033[32m'; D=$'\033[2m'; N=$'\033[0m'; else R=""; Y=""; G=""; D=""; N=""; fi
ERRS=0; WARNS=0
err()  { ERRS=$((ERRS+1));   printf '%s[ERROR]%s %s\n' "$R" "$N" "$*"; }
warn() { WARNS=$((WARNS+1));  printf '%s[WARN]%s  %s\n' "$Y" "$N" "$*"; }
info() { printf '%s[info]%s  %s\n' "$D" "$N" "$*"; }

HAS_HEAD=1; git rev-parse HEAD >/dev/null 2>&1 || HAS_HEAD=0
EMPTY_TREE=$(git hash-object -t tree /dev/null)

# ---- what is being checked -------------------------------------------------
RANGE=""
if [ "$STAGE" = "push" ]; then
  if git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then RANGE='@{u}..HEAD'; else RANGE="$EMPTY_TREE..HEAD"; fi
fi

diff_to_lines() {
  awk '/^\+\+\+ /{ f=substr($0,7); if ($0=="+++ /dev/null") f=""; next }
       /^@@/{ split($3,a,","); ln=substr(a[1],2)+0; next }
       /^\+/{ if (f!="") print f ":" ln ":" substr($0,2); ln++ }'
}

untracked_lines() {
  git ls-files --others --exclude-standard | while IFS= read -r f; do
    [ -f "$f" ] && grep -In '' -- "$f" 2>/dev/null | sed "s|^|$f:|"
  done
}

case "$STAGE" in
  commit) STREAM=$(git diff --cached -U0 --no-color | diff_to_lines)
          FILES=$(git diff --cached --name-only --diff-filter=ACMR) ;;
  push)   STREAM=$(git diff -U0 --no-color "$RANGE" | diff_to_lines)
          FILES=$(git diff --name-only --diff-filter=ACMR "$RANGE") ;;
  *)      if [ "$HAS_HEAD" -eq 1 ]; then
            STREAM=$( { git diff -U0 --no-color HEAD | diff_to_lines; untracked_lines; } )
            FILES=$( { git diff --name-only --diff-filter=ACMR HEAD; git ls-files --others --exclude-standard; } | sort -u )
          else
            STREAM=$( { git diff --cached -U0 --no-color | diff_to_lines; untracked_lines; } )
            FILES=$( { git diff --cached --name-only; git ls-files --others --exclude-standard; } | sort -u )
          fi ;;
esac

printf '%sHackAlem rules check (%s)%s\n' "$D" "$STAGE" "$N"

# ---- 1. secrets and .env (rules 5.6.6, 6.1.7; judged repos are read by others) ----
if [ -n "$FILES" ]; then
  while IFS= read -r f; do
    case "$f" in
      .env|*/.env|.env.*|*/.env.*)
        case "$f" in
          *.example|*.sample|*.template) ;;
          *) err "real env file would be committed: $f — remove it from git and add it to .gitignore" ;;
        esac ;;
    esac
  done <<< "$FILES"
fi

SECRET_NAMES=("Anthropic key" "OpenAI-style key" "NVIDIA key" "AWS access key" "GitHub token" "Slack token" "private key block")
SECRET_RES=('sk-ant-[A-Za-z0-9_-]{20,}' 'sk-[A-Za-z0-9]{32,}' 'nvapi-[A-Za-z0-9_-]{20,}' 'AKIA[0-9A-Z]{16}' 'gh[pousr]_[A-Za-z0-9]{30,}' 'xox[baprs]-[A-Za-z0-9-]{10,}' '-----BEGIN [A-Z ]*PRIVATE KEY-----')
i=0
while [ "$i" -lt "${#SECRET_RES[@]}" ]; do
  hits=$(printf '%s\n' "$STREAM" | grep -E -- "${SECRET_RES[$i]}" | grep -v '^\.env\.example:' | cut -d: -f1,2 | sort -u | head -5)
  if [ -n "$hits" ]; then
    for h in $hits; do err "possible ${SECRET_NAMES[$i]} at $h (value not shown) — remove it and rotate the key"; done
  fi
  i=$((i+1))
done
gen=$(printf '%s\n' "$STREAM" | grep -Ei -- "(api[_-]?key|secret|token|passw(or)?d)[\"' ]*[:=][\"' ]*[A-Za-z0-9_./+-]{24,}" | grep -v '^\.env\.example:' | cut -d: -f1,2 | sort -u | head -5)
for h in $gen; do warn "line looks like a hard-coded credential at $h — use an environment variable"; done

# ---- 2. official repo (5.4.9, 5.4.11, 5.9.2) ------------------------------------
URL=$(git remote get-url origin 2>/dev/null || true)
if [ -z "$URL" ]; then
  warn "no 'origin' remote: development must happen in the platform-created team repo (rules 5.4.9, 5.4.11, 5.9.2)"
elif [ -n "$REPO_REMOTE_PATTERN" ]; then
  case "$URL" in *"$REPO_REMOTE_PATTERN"*) ;; *) warn "origin is '$URL' but the team repo should match '$REPO_REMOTE_PATTERN' (rules 5.4.9, 5.9.2)" ;; esac
else
  info "REPO_REMOTE_PATTERN not set in .hackathon-rules.conf, so the remote is not verified"
fi

# ---- 3. competition window (5.3.1, 5.4.13) --------------------------------------
to_epoch() { TZ=Asia/Almaty date -j -f "%Y-%m-%d %H:%M" "$1" +%s 2>/dev/null || TZ=Asia/Almaty date -d "$1" +%s 2>/dev/null; }
NOW=$(date +%s); START_E=""; END_E=""
[ -n "$COMPETITION_START" ] && START_E=$(to_epoch "$COMPETITION_START")
[ -n "$COMPETITION_END" ]   && END_E=$(to_epoch "$COMPETITION_END")
IN_WINDOW=1
KIT_FILE_RE='^(\.claude/|\.vscode/|docs/|scripts/|AGENTS\.md$|CLAUDE\.md$|KIT\.md$|Makefile$|README\.md$|\.env\.example$|\.gitignore$|\.hackathon-rules\.conf$)'
if [ -n "$START_E" ] && [ "$NOW" -lt "$START_E" ]; then
  IN_WINDOW=0
  nonkit=$(printf '%s\n' "$FILES" | grep -Ev "$KIT_FILE_RE" | grep -v '^$' | head -5)
  if [ -n "$nonkit" ]; then
    warn "competition has not started ($COMPETITION_START Astana): only setup files should be committed now, not project work (rules 5.4.4.2, 5.4.5). Files: $(echo $nonkit | tr '\n' ' ')"
  fi
fi
if [ -n "$END_E" ] && [ "$NOW" -gt "$END_E" ]; then
  IN_WINDOW=0
  warn "competition ended ($COMPETITION_END Astana): the 18:00 repo state is the final version; later changes are not judged (rules 5.4.13, 5.4.14)"
fi
[ -z "$START_E" ] && [ -z "$END_E" ] && info "COMPETITION_START/END not set in .hackathon-rules.conf; time-window checks skipped"

# ---- 4. hourly evidence (5.4.8) — manual runs only -----------------------------
if [ "$STAGE" = "manual" ] && [ "$HAS_HEAD" -eq 1 ] && [ "$IN_WINDOW" -eq 1 ]; then
  last=$(git log -1 --format=%ct); age=$(( (NOW - last) / 60 ))
  if [ "$age" -ge "$HOURLY_MAX_MIN" ]; then
    warn "last commit was $age min ago: every hour of the competition needs a confirmed result, visible in the repo (rules 5.4.8, 5.9.2)"
  fi
fi

# ---- 5. large drops of code (5.4.4-5.4.6) --------------------------------------
NONKIT=$(printf '%s\n' "$STREAM" | grep -Ev "$KIT_FILE_RE" | grep -Ev '(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|uv\.lock|Cargo\.lock):' | grep -v '^$')
nlines=$(printf '%s\n' "$NONKIT" | grep -c . || true)
nfiles=$(printf '%s\n' "$NONKIT" | cut -d: -f1 | sort -u | grep -c . || true)
if [ "$nlines" -ge "$LARGE_COMMIT_LINES" ] || [ "$nfiles" -ge "$LARGE_COMMIT_FILES" ]; then
  warn "large drop of code: $nlines lines in $nfiles files. Be ready to show where it came from; disclose reused or third-party code in the README (rules 5.4.4, 5.4.5, 5.4.6)"
fi
vend=$(git ls-files | grep -E '(^|/)(node_modules|\.venv|venv|__pycache__)/' | head -1)
[ -n "$vend" ] && warn "dependency/cache folders are tracked (e.g. $vend): remove them from git and list dependencies in a manifest instead"

# ---- 6. personal ID / QR code (5.2.3, 5.2.6) -----------------------------------------
qr=$(printf '%s\n' "$FILES" | grep -iE '(^|/)[^/]*qr[^/]*\.(png|jpe?g|gif|svg|webp|pdf)$' | head -3)
[ -n "$qr" ] && warn "file looks like a QR code ($(echo $qr | tr '\n' ' ')): a participant's personal number / QR must never be shared or published (rules 5.2.3, 5.2.6)"

# ---- 7. docs the judges read (hard gate: rules 5.4.15, 5.4.16, 5.6.4) ------
if [ "$STAGE" != "commit" ]; then
  if [ ! -f README.md ]; then
    warn "README.md is missing: without it the project cannot pass technical review (rules 5.4.15, 5.4.16)"
  else
    missing=""
    for kw in "install" "run" "verif" "architecture" "depend" "requirement" "environment|configuration" "limitation" "prior code"; do grep -Eqi -- "$kw" README.md || missing="$missing '$kw'"; done
    [ -n "$missing" ] && warn "README.md does not mention:$missing. Experts must deploy it from the README alone or the team is out (rules 5.4.15, 5.4.16, 5.6.4)"
    ph=$(grep -cE '\{[A-Za-z][^{}]*\}' README.md || true)
    [ "$ph" -gt 0 ] && warn "README.md still has $ph template placeholder(s) like {...}"
  fi
  [ -f KIT.md ] && [ -f README.md ] && ! grep -qi "prior code" README.md && warn "the prepared kit is not disclosed: add a 'Prior code and sources' section to README.md (rule 5.4.4)"
  [ -f .env.example ] || warn ".env.example is missing: judges must be able to configure and run the project (rules 5.4.15, 5.6.4, 5.6.6)"
  if [ -f docs/TASK.md ] && grep -q '{…}' docs/TASK.md; then warn "docs/TASK.md is not filled in yet (mandatory task conditions unknown to the agents)"; fi
fi

# ---- 8. history rewriting (5.4.11, 5.9.2) — pre-push only -------------------------
if [ "$REFS" -eq 1 ]; then
  Z="0000000000000000000000000000000000000000"
  while read -r lref lsha rref rsha; do
    [ -z "${lsha:-}" ] && continue
    if [ "$lsha" = "$Z" ]; then warn "this push deletes remote ref $rref"; continue; fi
    if [ "$rsha" != "$Z" ] && ! git merge-base --is-ancestor "$rsha" "$lsha" 2>/dev/null; then
      warn "push rewrites remote history for $rref (force push / rebase): visible development history must be preserved (rules 5.4.11, 5.9.2)"
    fi
  done
fi

# ---- summary -------------------------------------------------------------------
echo
if [ "$ERRS" -eq 0 ] && [ "$WARNS" -eq 0 ]; then
  printf '%s[OK]%s no rule problems found. (Manual rules still apply: docs/HACKATHON_RULES.md)\n' "$G" "$N"
else
  echo "Result: $ERRS error(s), $WARNS warning(s). Details of each rule: docs/HACKATHON_RULES.md"
fi
if [ "$ERRS" -gt 0 ] && [ "${RULES_BLOCK:-1}" != "0" ]; then exit 1; fi
if [ "$WARNS" -gt 0 ] && [ "${RULES_STRICT:-0}" = "1" ]; then exit 1; fi
exit 0

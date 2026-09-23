#!/usr/bin/env bash
# Tells you (or an AI agent) whether pushing to GitHub is recommended right now.
# Read-only: it never commits or pushes.
#
# Usage: scripts/push-advice.sh
# Tunables (env): PUSH_MAX_AGE_MIN (default 40), PUSH_MAX_COMMITS (5), COMMIT_MAX_AGE_MIN (30)
set -uo pipefail

MAX_AGE="${PUSH_MAX_AGE_MIN:-40}"
MAX_COMMITS="${PUSH_MAX_COMMITS:-5}"
COMMIT_AGE="${COMMIT_MAX_AGE_MIN:-30}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "STATUS: not a git repository"; exit 0
fi

now=$(date +%s)
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "?")
has_commits=1; git rev-parse HEAD >/dev/null 2>&1 || has_commits=0
dirty=$(git status --porcelain | wc -l | tr -d ' ')
remote=$(git remote | head -1)

reasons=()
level="OK"

if [ "$has_commits" -eq 0 ]; then
  echo "STATUS: no commits yet ($dirty changed files)"
  [ "$dirty" -gt 0 ] && echo "ADVICE: COMMIT — make a first commit, then push."
  exit 0
fi

last_commit_ts=$(git log -1 --format=%ct)
last_commit_min=$(( (now - last_commit_ts) / 60 ))

unpushed=0; oldest_unpushed_min=0; upstream_note=""
if git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
  unpushed=$(git rev-list --count '@{u}..HEAD')
  if [ "$unpushed" -gt 0 ]; then
    oldest_ts=$(git log '@{u}..HEAD' --format=%ct | tail -1)
    oldest_unpushed_min=$(( (now - oldest_ts) / 60 ))
  fi
elif [ -n "$remote" ]; then
  upstream_note="branch '$branch' has never been pushed"
  unpushed=$(git rev-list --count HEAD)
  oldest_ts=$(git log --format=%ct | tail -1)
  oldest_unpushed_min=$(( (now - oldest_ts) / 60 ))
else
  upstream_note="no git remote configured"
fi

echo "Branch: $branch | uncommitted files: $dirty | unpushed commits: $unpushed | last commit: ${last_commit_min} min ago"
[ -n "$upstream_note" ] && echo "Note: $upstream_note"

if [ -n "$remote" ]; then
  if [ "$unpushed" -gt 0 ] && [ "$oldest_unpushed_min" -ge "$MAX_AGE" ]; then
    level="HIGH"; reasons+=("oldest unpushed commit is ${oldest_unpushed_min} min old (limit ${MAX_AGE})")
  fi
  if [ "$unpushed" -ge "$MAX_COMMITS" ]; then
    level="HIGH"; reasons+=("$unpushed commits are not on GitHub (limit $MAX_COMMITS)")
  fi
  if [ -n "$upstream_note" ] && [ "$unpushed" -gt 0 ]; then
    level="HIGH"; reasons+=("$upstream_note")
  fi
else
  level="NOREMOTE"; reasons+=("no remote: nothing can be pushed until the team repo remote is set")
fi

if [ "$dirty" -gt 0 ] && [ "$last_commit_min" -ge "$COMMIT_AGE" ]; then
  [ "$level" = "OK" ] && level="COMMIT"
  reasons+=("$dirty uncommitted files and the last commit was ${last_commit_min} min ago (limit ${COMMIT_AGE}): commit, then push")
fi

case "$level" in
  HIGH)   echo "ADVICE: RECOMMEND PUSH NOW";;
  COMMIT) echo "ADVICE: RECOMMEND COMMIT NOW, then push";;
  NOREMOTE) echo "ADVICE: NO REMOTE — clone the team repo or add its remote before relying on backups";;
  *)      echo "ADVICE: OK — no push needed yet";;
esac
if [ "${#reasons[@]}" -gt 0 ]; then for r in "${reasons[@]}"; do echo "  - $r"; done; fi
exit 0

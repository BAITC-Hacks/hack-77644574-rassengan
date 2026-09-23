#!/usr/bin/env bash
# Installs (or removes) the kit's git hooks in the current repository.
# Usage: scripts/install-hooks.sh [--uninstall]
# Never replaces a hook that was not installed by this kit.
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
HOOKDIR=$(git rev-parse --git-path hooks)
mkdir -p "$HOOKDIR"
MARK="hackathon-kit hook"
for h in pre-commit pre-push; do
  src="$ROOT/scripts/hooks/$h"; dst="$HOOKDIR/$h"
  if [ "${1:-}" = "--uninstall" ]; then
    if [ -f "$dst" ] && grep -q "$MARK" "$dst"; then rm -f "$dst"; echo "removed $h"; fi
    continue
  fi
  [ -f "$src" ] || { echo "missing $src"; continue; }
  if [ -e "$dst" ] && ! grep -q "$MARK" "$dst"; then
    echo "SKIPPED $h: an existing hook that is not from the kit is at $dst"; continue
  fi
  cp "$src" "$dst"; chmod +x "$dst"; echo "installed $h"
done

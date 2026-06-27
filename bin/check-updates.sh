#!/bin/sh
# check-updates.sh — optional update notifier for the explainer-system repo
#
# Usage:
#   source /path/to/repo/bin/check-updates.sh    (in your shell rc file)
#   OR
#   /path/to/repo/bin/check-updates.sh           (run directly)
#
# Works on bash, zsh, dash, fish. Only alerts if unpulled commits exist.

EXPLAINER_REPO="${EXPLAINER_REPO:-$(cd "$(dirname "$0")/.." && pwd)}"

# Silent exit if repo doesn't exist
[ -d "$EXPLAINER_REPO/.git" ] || return 0 2>/dev/null || exit 0

# Fetch updates (silent)
(cd "$EXPLAINER_REPO" && git fetch origin 2>/dev/null) || return 0 2>/dev/null || exit 0

# Count commits behind remote
BEHIND=$(cd "$EXPLAINER_REPO" && git rev-list --count HEAD..origin/main 2>/dev/null)

# Alert if behind
if [ "$BEHIND" -gt 0 ] 2>/dev/null; then
  printf "\n"
  printf "\033[33m📦 explainer-system: %d new commit(s) available\033[0m\n" "$BEHIND"
  printf "   cd %s && git pull\n" "$EXPLAINER_REPO"
  printf "\n"
fi

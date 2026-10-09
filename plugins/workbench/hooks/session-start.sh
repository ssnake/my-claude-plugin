#!/usr/bin/env bash
# Concatenates every instructions/*.md file and returns it as SessionStart additionalContext.

set -euo pipefail

instructions_dir="${CLAUDE_PLUGIN_ROOT}/instructions"

shopt -s nullglob
files=("$instructions_dir"/*.md)
[ ${#files[@]} -eq 0 ] && exit 0

for f in "${files[@]}"; do
  cat "$f"
  printf '\n\n'
done | jq -Rs '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: .
  }
}'

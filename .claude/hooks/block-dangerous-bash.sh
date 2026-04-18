#!/usr/bin/env bash
# PreToolUse hook — block dangerous patterns in Bash commands.
# stdin: Claude Code JSON ({tool_name, tool_input, ...}).
# exit 2: command blocked (stderr message shown to user).
# exit 0: pass.

set -e

input=$(cat)
command=$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command",""))' 2>/dev/null || echo "")

if [ -z "$command" ]; then
  exit 0
fi

# Dangerous patterns (permission deny is declarative — this hook provides runtime blocking)
if printf '%s' "$command" | grep -qE '(^|[ ;&|])rm[[:space:]]+-rf[[:space:]]+/($|[[:space:]])'; then
  echo "[hook BLOCKED] rm -rf / is not allowed." >&2
  exit 2
fi
if printf '%s' "$command" | grep -qE 'git[[:space:]]+push[[:space:]]+(--force|-f)[[:space:]]+.*\b(main|master)\b'; then
  echo "[hook BLOCKED] force push to main/master is not allowed." >&2
  exit 2
fi
if printf '%s' "$command" | grep -qE '(curl|wget)[[:space:]]+[^|]+\|[[:space:]]*(sh|bash)'; then
  echo "[hook BLOCKED] curl|sh / wget|sh pipe execution is not allowed." >&2
  exit 2
fi

exit 0

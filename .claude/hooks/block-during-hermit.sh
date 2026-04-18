#!/usr/bin/env bash
# PreToolUse hook — block CC Edit/Write while a HermitAgent task is running.
# Lock file: .hermit/active-task.lock (in project cwd)
#
# exit 2: blocked (message delivered via stderr)
# exit 0: allowed
#
# stdin: {"tool_name": "Edit|Write|NotebookEdit|...", "tool_input": {...}, "cwd": "..."}

set -e

input=$(cat 2>/dev/null || echo "{}")

tool_name=$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tool_name",""))' 2>/dev/null || echo "")

# Only target Edit/Write/NotebookEdit
case "$tool_name" in
  Edit|Write|NotebookEdit|MultiEdit) ;;
  *) exit 0 ;;
esac

# Determine cwd (use cwd from hook input if present, otherwise PWD)
cwd=$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("cwd","") or "")' 2>/dev/null || echo "")
cwd="${cwd:-$PWD}"

lock="$cwd/.hermit/active-task.lock"

if [ ! -f "$lock" ]; then
  exit 0
fi

# Extract lock content (maintain blocking even if parsing fails)
task_id=$(python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get("task_id", "?"))
except Exception:
    print("?")
' "$lock" 2>/dev/null || echo "?")
skill=$(python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get("skill", "?"))
except Exception:
    print("?")
' "$lock" 2>/dev/null || echo "?")

cat >&2 <<EOF
[hook BLOCKED] HermitAgent task in progress — CC Edit/Write blocked.
  task_id: $task_id
  skill:   $skill
  lock:    $lock

Wait or cancel with mcp__hermit__cancel_task("$task_id") and retry.
EOF

exit 2

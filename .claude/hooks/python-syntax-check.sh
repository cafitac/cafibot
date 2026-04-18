#!/usr/bin/env bash
# PostToolUse hook — lightweight syntax check after Python files are modified.
# stdin: Claude Code JSON ({tool_name, tool_input, tool_response, ...}).
# exit 0: pass (syntax errors are only printed to stderr, not treated as failure — informational feedback).

set -e

input=$(cat)
file=$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); ti=d.get("tool_input",{}); print(ti.get("file_path") or ti.get("path") or "")' 2>/dev/null || echo "")

if [ -z "$file" ] || [ ! -f "$file" ]; then
  exit 0
fi

case "$file" in
  *.py)
    if ! python3 -c "import ast; ast.parse(open('$file').read())" 2>/tmp/cc-hook-syntax.err; then
      echo "[hook] ⚠️  Python syntax error in $file:" >&2
      cat /tmp/cc-hook-syntax.err >&2
    fi
    ;;
esac

exit 0

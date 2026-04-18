#!/usr/bin/env bash
# measure-savings.sh — produce a Claude-side cost comparison from two
# Claude Code session JSONL files. Hermit executor usage is intentionally
# ignored (ollama = free, z.ai = flat-rate).
#
# Usage:
#   scripts/measure-savings.sh \
#     --session-a ~/.claude/projects/<proj>/<session-A>.jsonl \
#     --session-b ~/.claude/projects/<proj>/<session-B>.jsonl \
#     [--claude-price-in 3.0]      # USD per 1M input tokens
#     [--claude-price-out 15.0]    # USD per 1M output tokens

set -euo pipefail

# Defaults — Sonnet 4.x list prices per 1M tokens.
PRICE_IN=3.0
PRICE_OUT=15.0

usage() { sed -n '2,12p' "$0"; exit 1; }

SESSION_A="" SESSION_B=""
while [ $# -gt 0 ]; do
  case "$1" in
    --session-a) SESSION_A="$2"; shift 2 ;;
    --session-b) SESSION_B="$2"; shift 2 ;;
    --claude-price-in) PRICE_IN="$2"; shift 2 ;;
    --claude-price-out) PRICE_OUT="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "unknown arg: $1" >&2; usage ;;
  esac
done

for v in SESSION_A SESSION_B; do
  if [ -z "${!v}" ]; then echo "missing --${v,,}" >&2; usage; fi
done
for f in "$SESSION_A" "$SESSION_B"; do
  [ -f "$f" ] || { echo "not found: $f" >&2; exit 2; }
done

# Sum the Claude usage fields from every assistant message in a session
# JSONL. Claude Code records usage as either {"message":{"usage":...}}
# or {"usage":...}. Both shapes are handled.
python3 - "$SESSION_A" "$SESSION_B" <<'PY' > /tmp/hermit-measure-tokens.txt
import json, sys
for path in sys.argv[1:]:
    tin = tout = tcache_c = tcache_r = 0
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            usage = obj.get("message", {}).get("usage") or obj.get("usage")
            if not isinstance(usage, dict):
                continue
            tin += int(usage.get("input_tokens", 0) or 0)
            tout += int(usage.get("output_tokens", 0) or 0)
            tcache_c += int(usage.get("cache_creation_input_tokens", 0) or 0)
            tcache_r += int(usage.get("cache_read_input_tokens", 0) or 0)
    print(f"{tin} {tout} {tcache_c} {tcache_r}")
PY

read IN_A OUT_A CC_A CR_A < <(sed -n '1p' /tmp/hermit-measure-tokens.txt)
read IN_B OUT_B CC_B CR_B < <(sed -n '2p' /tmp/hermit-measure-tokens.txt)

cost() {
  python3 -c "print(round(($1*$PRICE_IN + $2*$PRICE_OUT)/1_000_000, 3))"
}

pct() { # percentage change from A to B; negative number means B spent less
  python3 -c "a=$1; b=$2
print('—' if a == 0 else f'{(b/a - 1)*100:+.0f}%')"
}

COST_A=$(cost "$IN_A" "$OUT_A")
COST_B=$(cost "$IN_B" "$OUT_B")

fmt() { printf "%'d" "$1" 2>/dev/null || echo "$1"; }

cat <<EOF

|                        | Pure Claude Code (A) | CC + HermitAgent (B) | Δ      |
|------------------------|---------------------:|---------------------:|-------:|
| Claude input tokens    | $(fmt "$IN_A")       | $(fmt "$IN_B")       | $(pct "$IN_A"  "$IN_B") |
| Claude output tokens   | $(fmt "$OUT_A")      | $(fmt "$OUT_B")      | $(pct "$OUT_A" "$OUT_B") |
| Claude cache read      | $(fmt "$CR_A")       | $(fmt "$CR_B")       | —      |
| **Claude-side cost**   | **\$$COST_A**        | **\$$COST_B**        | **$(pct "$COST_A" "$COST_B")** |

_Pricing: \$${PRICE_IN}/1M input, \$${PRICE_OUT}/1M output. Override with
\`--claude-price-in\` / \`--claude-price-out\`. Hermit executor cost is
treated as \$0 (ollama = free, z.ai / GLM = flat-rate)._
EOF

rm -f /tmp/hermit-measure-tokens.txt

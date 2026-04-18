#!/usr/bin/env bash
# Fake Claude Code session for the README demo GIF.
# Called from scripts/demo.tape via vhs. Prints the *pattern* of a
# Claude-orchestrator / Hermit-executor flow with timed sleeps. No
# numeric claims — real cost data lives under benchmarks/.
#
# Self-locates so it works regardless of the caller's cwd.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." 2>/dev/null || true

# ANSI colours
Y='\033[1;33m' ; C='\033[1;36m' ; G='\033[1;32m' ; R='\033[1;31m'
D='\033[2m' ; B='\033[1m' ; N='\033[0m'

s()    { sleep "$1"; }
line() { printf "%b\n" "$1"; }

line "${D}# Baseline — pure Claude Code${N}"
s 0.4
line "${B}user>${N} /feature-develop <task>"
s 0.3
line "${Y}▸${N} Claude reads files..."
s 0.3
line "${Y}▸${N} Claude runs pytest..."
s 0.3
line "${Y}▸${N} Claude writes edits..."
s 0.3
line "${Y}▸${N} Claude writes commit message..."
s 0.3
line ""
line "${R}Every tool call and tool output lands in Claude's context.${N}"
s 1.0

line ""
line "${D}─────────────────────────────────────────────${N}"
line ""
s 0.3

line "${D}# With HermitAgent — same task${N}"
s 0.3
line "${B}user>${N} /feature-develop-hermit <task>"
s 0.3
line "${C}[Claude]${N} Interview: endpoints? validation? OK, plan saved."
s 0.4
line "${C}[Claude]${N} → mcp__hermit__run_task(plan)"
s 0.3
line "${G}[Hermit]${N}  reading files...    (executor, \$0)"
s 0.25
line "${G}[Hermit]${N}  running tests...    (executor, \$0)"
s 0.25
line "${G}[Hermit]${N}  applying edits...   (executor, \$0)"
s 0.25
line "${G}[Hermit]${N}  green. summary returned."
s 0.3
line "${C}[Claude]${N} Summary: 3 files touched, tests pass."
s 0.4
line ""
line "${G}Claude's context saw only the interview + the summary.${N}"
line "${D}Measure your own savings: benchmarks/ + scripts/measure-savings.sh${N}"
s 1.8

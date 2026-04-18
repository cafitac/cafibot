# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/).
This project has not yet hit a tagged release; the entries below describe work merged into `main`.

## Unreleased

### Added
- 3-Layer Harness (Layer A/B/C) separating Claude Code config, HermitAgent primitives, and spawned-tool env
- `/doctor` — 5-axis setup diagnostics (`hermit_agent/doctor.py`)
- `/plan save|list|load` — plan artifacts under `.hermit/plans/` (`hermit_agent/plans.py`)
- `/wrap` — session handoff to `.hermit/handoffs/`, auto-trigger via `HERMIT_AUTO_WRAP=1` (`hermit_agent/session_wrap.py`)
- `/init` — scaffold a `HERMIT.md` in the current directory
- Skill `audience` frontmatter field — explicit CC/HermitAgent sharing control
- Progressive disclosure for `HERMIT.md` / `.hermit/rules/` — `depth="shallow"|"deep"` loader
- Permission floor — `.env`, `*.pem`, `*.key`, `credentials*`, `secrets*` blocked across every mode
- Verifier strictness — mandatory `VERDICT: PASS|FAIL` output + `parse_verdict()` helper
- `auto_verify` cooldown + modified-files guard to avoid wasted verifier runs
- `.hermit/rules/` loader wired into dynamic context + compact reminders + skill execution
- `cc-learner.py` — independent Python script for Claude Code learned-skill lifecycle (separate from HermitAgent's own learner)
- MCP Server thin proxy to the Gateway + `/health` endpoint + channel notify logging

### Changed
- MCP Server is now a thin proxy delegating to the AI Gateway over REST/SSE
- `hermit_agent/loop.py::_preprocess_slash_command` moved out of `mcp_server.py` and reused across transports
- Permission defaults tightened to `ALLOW_READ` for gateway-spawned agents
- Skills: `feature-*` and `code-*` default model switched to `sonnet`; `opus` explicitly disallowed for cost reasons
- `/feature-develop[-hermit_agent]`, `/feature-register[-debate]`, `/feature-init` now inject an optional `ralplan` consensus phase before the deep-interview

### Removed
- Debate skill family (`debate`, `feature-*-debate`, `code-*-debate`, `debate-templates/`) — superseded by `ralplan`

### Docs
- `.dev/learner-spec.md` — learned-skill lifecycle and model-swap handling
- `.dev/hermit_agent_harness_spec.md` — Layer B design
- `.dev/harness-layer-c-trace.md` — HermitAgent ↔ Claude Code boundary analysis
- `.harness/check-reports/` — harness maturity audit snapshots

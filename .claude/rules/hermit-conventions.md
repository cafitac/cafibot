# HermitAgent Project-Specific Rules

Follow all global rules (`~/.claude/rules/code-rules.md`, `workflow-rules.md`), and additionally comply with the rules below for this project.

## Layer Separation [P1]

| Layer | Location | Scope |
|---|---|---|
| A | `CLAUDE.md`, `.claude/` | When Claude Code handles this repo |
| B | `HERMIT.md`, `hermit_agent/hooks.py`, `hermit_agent/skills.py` | HermitAgent core features |
| C | (dynamic) — env/args HermitAgent passes when spawning Claude Code | Runtime |

No layer mixing: Layer A settings stay out of `hermit_agent/`; Layer B code stays out of `.claude/`.

## Directory Boundaries [P1]

- `src/` — Claude Code original reference. **Read-only. No modifications, additions, or deletions.**
- `claw-code-main/`, `hermes-agent/` — External repo clones. No modifications.
- `hermit_agent/` — HermitAgent code only.

## Document Management [P2]

- `docs/` — Human-managed. AI is read-only; explicit user approval required to modify.
- `.dev/` — AI-managed. Write analysis/design docs here; humans promote to `docs/`.

## Gateway Scope [P2]

`hermit_agent/gateway/` is LLM relay infrastructure only. No harness primitives (hooks, skills, CLAUDE.md loader). See `hermit-gateway-rules.md` for details.

## HermitAgent Standard [P1]

HermitAgent uses Claude Code as the standard. No arbitrary feature additions. When reproducing CC behavior, read `src/` carefully — don't guess.

## Tests [P1]

- `pytest` — Ollama-dependent tests auto-excluded via `conftest.py`.
- TDD Red-Green Cycle required. External API/LLM calls use mocks; internal logic uses real objects.

## Sensitive Information [P1]

- `.env` variants, `*.pem`, `*.key`, `credentials*` registered in `.gitignore` + `.claude/settings.json` deny list.
- New sensitive patterns: update both places.

## QA Method [P2]

Background execution + log polling + intervention on anomaly detection. Details: `~/.claude/projects/-Users-reddit-Project-claude-code/memory/feedback_hermit_agent_qa_method.md`

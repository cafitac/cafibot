# HermitAgent Harness Spec (Layer B)

**Written Date**: 2026-04-17
**Input**: check-harness report (`.harness/check-reports/check-harness-2026-04-17-both/report.md`), Layer C analysis (`.dev/harness-layer-c-trace.md`)
**Purpose**: Define the harness primitives HermitAgent will provide to its user, and organize what is currently implemented and what is missing.

## Design Principles

1. **Claude Code Standard Compliance** — Keep feature names/file locations/semantics identical to Claude Code. Arbitrary feature addition prohibited (global feedback rule).
2. **File Location Separation** — HermitAgent-specific configurations are under `~/.hermit/`. `~/.claude/` is exclusively for Claude Code. If sharing is needed, make it explicit.
3. **Layer Isolation** — Layer B (HermitAgent feature) and Layer C (Claude Code executed by HermitAgent) must not contaminate each other.

## 6-Axis Gap Map

| Axis | Requirement | Current Implementation | Gap |
|---|---|---|---|
| **1. Structure** | skill portfolio management | `hermit_agent/skills.py` — `~/.hermit/skills/` + `~/.claude/skills/` loader | No skill health audit (dead/ghost/duplicate detection) |
| **2. Context** | Project context load | `hermit_agent/loop.py:36 _find_project_config` — global(`~/.hermit/HERMIT.md`) + project(`HERMIT.md`/`.hermit_agent.md`) walk-up. 6 regression tests (`tests/test_project_config_loader.py`). | Progressive Disclosure (depth-based loading), `.hermit/rules/` separation unimplemented |
| **3. Planning** | plan-first workflow | Only `plan` mode exists in `hermit_agent/permissions.py` (read-only + write blocked) | No plan artifact save/reference functionality |
| **4. Execution** | Sub-agent delegation / parallel | `hermit_agent/tools/agent/subagent.py`, `hermit_agent/auto_agents.py` | (Sufficient) |
| **5. Verification** | Pre-completion verifier | `auto_agents.py` VERIFIER type + SYSTEM_PROMPT + subagent.py registration + `detect_auto_agent` "done" trigger. Separate strict verifier in `ralph.py`. | `auto_verify` defaults to False (cost). VERIFIER_PROMPT is at the "recommend test execution" level, lacking strict verification against acceptance criteria. |
| **6. Improvement** | Inter-session learning | `hermit_agent/memory.py`, `hermit_agent/learner.py`, `hermit_agent/session_logger.py` | session-wrap equivalent (auto handoff save on exit) insufficient |

## Required Primitives — Implementation Status

### ✅ Already Implemented
- `hermit_agent/hooks.py` — PreToolUse/PostToolUse (config: `~/.hermit/hooks.json`)
- `hermit_agent/skills.py` — SKILL.md loader (shared `~/.hermit/skills/` + `~/.claude/skills/`)
- `hermit_agent/permissions.py` — 6 modes + **sensitive file deny floor** (Priority 1 complete)
- `hermit_agent/memory.py` — MEMORY.md index + frontmatter files
- `hermit_agent/session.py` — session save/restore
- `hermit_agent/context.py` — autocompact
- `hermit_agent/auto_agents.py` — **verifier subagent_type + auto-trigger (Priority 2 practically complete)**
- `hermit_agent/loop.py:_find_project_config` — **HERMIT.md loader (Priority 1 verified)**

### ⚠️ Partial
- **verifier strictness**: Works, but VERIFIER_PROMPT is only at the "recommend test execution" level. Enforcing acceptance criteria only applies to the strict verifier in `ralph.py`.
- **auto_verify default off**: Due to cost/frequency considerations. Activation conditions need to be determined.
- **session-wrap equivalent**: HermitAgent lacks automatic handoff saving on session exit (unlike Claude Code's session-wrap skill).

### ❌ Not Implemented (New Tasks)
- **skill portfolio audit**: Diagnostic feature like `/check-harness`. Detects skill duplication, trigger conflicts, and ghost references.
- **plan artifact storage**: Save plans created in plan mode to `.hermit/plans/` for future reference.
- **`.hermit/rules/` separation**: Project-specific rules directory not implemented.
- **Progressive Disclosure**: Adjust context load level with `depth=shallow/deep`.
- **Hard Completion Gate**: Enforced logic requiring no pending tasks + passing tests + verifier pass set to be acknowledged as "done".

## Layer A ↔ Layer B Sharing/Separation Decision

| Item | Location | Remarks |
|---|---|---|
| CLAUDE.md (Layer A) | `CLAUDE.md` | Loaded only by Claude Code |
| HERMIT.md (Layer B) | `HERMIT.md` | Loaded only by HermitAgent — maintains role separation |
| rules/ (Layer A) | `.claude/rules/` | Claude Code only |
| rules/ (Layer B) | **`~/.hermit/rules/` (Newly proposed)** | Dedicated rules separated for HermitAgent |
| skills/ | `~/.claude/skills/`, `~/.hermit/skills/` | Currently shared by both — full separation recommended for mid-to-long term (refer to Layer C trace document) |
| hooks | `.claude/settings.json` (A), `~/.hermit/hooks.json` (B) | Structural separation complete |
| memory | `~/.claude/projects/*/memory/` (A), `~/.hermit/memory/` (B) | Separation complete |

## Roadmap (Priority)

### Priority 1 (Fast ROI) — ✅ Complete
1. ✅ HermitAgent loader reads project-local `HERMIT.md` (Verification complete — already implemented, regression tests added)
2. ✅ `hermit_agent/permissions.py` sensitive file deny floor (Applied to all modes, 27 tests green)

### Priority 2 (Mid-term)
3. ✅ `verifier` subagent_type — SYSTEM/TASK prompt strictness tuning completed (RUN-not-suggest, strict `VERDICT: PASS|FAIL` enforcement). Added `parse_verdict()` helper. 10 tests green.
4. ✅ plan artifact saving (`.hermit/plans/{timestamp}_{slug}.md`) — `hermit_agent/plans.py` save/load/list, `/plan save|list|load` slash command, 10 tests green.
5. ✅ `/doctor` slash command — `hermit_agent/doctor.py` 5-axis diagnostic (HERMIT.md / ~/.hermit dir / hooks.json / skills / permissions floor). 11 tests green. Advanced audit (duplicates/ghosts) to follow.

### Priority 3 (Long-term)
6. ✅ Explicit sharing metadata — `SKILL.md` frontmatter `audience:` field. Loads in HermitAgent if value is `hermit_agent`/`both`/`all`/`<list including hermit_agent>`. Skip `claude-code` exclusives. Missing field = backwards-compat load. 9 tests green.
7. ✅ Progressive Disclosure — `_find_project_config(cwd, depth="deep"|"shallow")`. shallow=cwd only, deep=global+walk-up. 6 tests green.
8. ✅ `/wrap` slash command — `hermit_agent/session_wrap.py` `build_handoff` / `save_handoff`. `.hermit/handoffs/{ts}_{session_id}.md`. 6 tests green.

### Follow-up — ✅ Completed
- ✅ `.hermit/rules/` loader (`_find_rules(cwd, depth)`) + `_load_rules` extension — project rule injection across all dynamic context, compact, and skill execution. 10 tests green.
- ✅ auto_verify condition tuning — triggers only when `modified_files` are present + `verify_cooldown_turns` (default 5) cooldown. 8 tests green.
- ✅ `/wrap` auto-trigger — auto-saves handoff at `shutdown()` when `HERMIT_AUTO_WRAP=1` env is set. 5 tests green.

## Out of Scope

- **Gateway (`hermit_agent/gateway/`)** — handles LLM relaying only. Does not include harness features (adjacent infrastructure maintains 429, token saving, routing).
- **model-level changes** — does not intervene in the LLM's own prompt/pretraining.

## Verification Method

- Write pytest tests for each primitive (TDD red-green).
- Collect tests following the `hermit_agent/tests/test_harness_*.py` convention.
- Ensure via regression tests that changes to Layer B do not affect Layer A.

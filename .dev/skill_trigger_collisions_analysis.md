# Analysis & Resolution of 7 Skill Trigger Conflicts

**Date**: 2026-04-17
**Input**: `/tmp/cc-cache/check-harness/PORTFOLIO.json` (check-harness A5 check results)
**Principle**: **Description refinement + documentation** instead of forced rename. The intended namespace family is maintained.

---

## 1. KB family (5 items) — ✅ Cleanup complete

**Skills**: `kb`, `kb-query`, `kb-edit`, `kb-ingest`, `kb-lint`
**Nature**: Intended namespace (umbrella + sub-ops)
**Action**: Specify dispatcher role in `~/.claude/skills/kb/SKILL.md` description + add sub-skill list. The rest of the kb-* are already specific, so they remain unchanged.

## 2. harness cluster (3 items) — ✅ Partially cleaned up

**Skills**: `check-harness` (diagnostics), `harness-audit` (configuration optimization), `harness:harness` (plugin, agent architect)
**Action**:
- Update `check-harness` description:
- Remove `"harness audit"` from triggers (transfer exclusive use to harness-audit)
- Add "Distinction from sibling skills" section — specify roles of the three: diagnostics/optimization/building
- Emphasize **"Does not modify"** (vs harness-audit)
- `harness-audit` — Already configured with `disable-model-invocation: true` to prevent automatic invocation, so OK as is.
- `harness:harness` — **Plugin-managed file** (`~/.claude/plugins/cache/harness-marketplace/...`). Edits get overwritten on plugin update. Its description includes `"harness check"` which overlaps with `check-harness`, but description refinement on the plugin side should be reported upstream (revfactory/harness). **Action deferred for this session** — `harness:harness` should only be used when the user intentionally invokes it for "build/design" requests.

## 3. debug cluster (3 items) — ⊗ No action needed

**Skills**: `sentry-cli`, `settlement-debug`, `sentry-debug`
**Verdict**: Mechanical collision grouped by a single keyword `"debug"`. Each description is already domain-specific (Sentry CLI / Pre-settlement CS / Sentry URL analysis). Low risk of actual invocation confusion.
**Action**: None.

## 4. review cluster (4 items) — ⊗ No action needed

**Skills**: `code-review`, `code-polish`, `harness-audit`, `guardrail-review`
**Verdict**: Shares the word `"review"` but scopes are completely separated (PR review / code implementation / harness optimization / guardrail suggestions). Descriptions are already clear via scope-naming.
**Action**: None.

## 5. session cluster (2 items) — ⊗ No action needed

**Skills**: `session-wrap`, `oh-my-claudecode:project-session-manager`
**Verdict**: Only shares the word `"session"`. Actual functionality is **coding session-end cleanup** vs **tmux/worktree-based dev environment isolation** — completely different. project-session-manager is distinguishable by its OMC namespace prefix.
**Action**: None (if needed, a line "Refer to project-session-manager for dev env management" can be added to the session-wrap description — low priority).

## 6. diagnos cluster (3 items) — ⊗ No action needed

**Skills**: `check-harness`, `harness-audit`, `oh-my-claudecode:omc-doctor`
**Verdict**: Shares "diagnostics" but targets are completely separated (Claude Code harness / same + optimization / OMC installation issues). The distinction from harness-audit is clarified by updating the check-harness description. omc-doctor is distinguished by its namespace prefix.
**Action**: None.

## 7. Sentry cluster (2) — ⊗ Action not required

**Skill**: `sentry-cli` (CLI docs), `sentry-debug` (Multiple URL analysis)
**Verdict**: Both are Sentry-related but clearly separated into **document reference vs. execution workflow**. The description is already distinguishable.
**Action**: None.

---

## Final Status

| Cluster | Action | Status |
|---|---|---|
| KB (5) | kb description refinement | ✅ Done |
| harness (3) | check-harness description refinement, confirm blocking of harness-audit auto-invocation, harness:harness is a plugin — upstream issue required | ⚠️ Partial |
| debug (3) | - | ⊗ Not required (mechanical collision) |
| review (4) | - | ⊗ Not required |
| session (2) | - | ⊗ Not required |
| diagnos (3) | Automatically resolved by check-harness update | ⊗ Not required |
| Sentry (2) | - | ⊗ Not required |

**Core perspective**: Keyword overlap ≠ actual confusion. The A5 checklist quantifies by keyword count, but if the description scope is clear, the LLM dispatches correctly. Out of the 7 cases, only **2 (KB, harness)** were substantial improvement targets, and the actions are complete.

## Follow-up suggestions

- **harness:harness plugin description** — Upstream issue for revfactory/harness repo: recommend transferring `"harness check"` / `"harness audit"` keywords exclusively to check-harness.
- **check-harness A5 judgment logic improvement** — Redefining it to "whether there are multiple skills in the same scope" instead of a keyword count reduces false positives.

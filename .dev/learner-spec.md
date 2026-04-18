# Learner Spec — Learned Skill Lifecycle & Model Version Handling

**Date**: 2026-04-17
**Author**: AI (in `.dev/` pending human review → promote to `docs/`)
**Target systems**: HermitAgent (independent), Claude Code (independent). **Spec shared, code not shared**.
**Purpose**: Ensure learned skills persist long-term and are automatically pruned across model upgrades, project moves, and framework changes.

---

## 1. Principles

1. **CC ⊥ HermitAgent** — Repository, code, and execution are fully independent. Only this spec's **frontmatter format and lifecycle semantics** are shared.
2. **HermitAgent is an all-in-one plugin aggregator** — Runs independently without Claude Code. Targeted at external users.
3. **CC is a Claude-model-exclusive harness** — Only features from HermitAgent that are net-positive in CC are selectively ported. Net-negative → skip port.
4. **Skill validity changes over time, across model changes, and across project switches** — Manage as a living portfolio, not a static store.

---

## 2. Independence Invariants

| Boundary | CC depends on HermitAgent? | HermitAgent depends on CC? |
|---|:---:|:---:|
| import | ❌ | ❌ |
| Executable binary | ❌ | ❌ |
| Config files | ❌ (`~/.claude/` vs `~/.hermit/` separation) | ❌ |
| Learning store | ❌ | ❌ |
| Dashboard | ❌ | ❌ |
| **Spec doc (this file)** | ✅ (reference) | ✅ (reference) |
| **Skill frontmatter format** | ✅ (common schema) | ✅ (common schema) |

**Result**: HermitAgent open-source users can use the learner fully without Claude Code.

---

## 3. Directory Layout

### HermitAgent (existing + enhanced)
```
~/.hermit/skills/
├── learned-feedback/       # Explicit user feedback ("don't do this")
│   ├── pending/            # First detection, not yet verified
│   ├── approved/           # After pytest pass or user approval
│   └── deprecated/         # Automatically deprecated
└── auto-learned/           # HermitAgent self-learning (session pattern extraction)
    ├── (no pending — auto-promoted)
    └── (deprecated shown via status=deprecated in same directory, or separate subdir — implementation choice)
```

### Claude Code (lifecycle restoration needed)
```
~/.claude/skills/
├── learned-feedback/
│   ├── pending/
│   ├── approved/           # ★ Move current root flat files here
│   └── deprecated/
└── auto-learned/           # ★ New — CC self-learning. Pattern extraction via session-wrap hook
```

**Note**: The 10 flat `feedback_*.md` files currently at `~/.claude/skills/learned-feedback/` root will be moved to `approved/` in Phase 2.

### Project-local (optional)
```
{project}/.claude/skills/learned-feedback/{pending,approved,deprecated}/   # CC project skills
{project}/.hermit/skills/learned-feedback/...                             # HermitAgent project skills
```

Project-local skills are loaded **only for that project**. Even with frontmatter `projects: ["*"]`, if local exists only local is read (local-first).

---

## 4. Frontmatter Schema (shared)

```yaml
---
# Required
name: string                          # Should match filename
type: learned-feedback | auto-learned
status: pending | approved | needs_review | deprecated
description: string                   # 1-line summary, displayed by audience/loader
learned_from: "YYYY-MM-DD + context"

# Model version handling
learned_on_model: string              # Original learning model (immutable). e.g.: claude-opus-4-6, glm-5.1, qwen3-coder:30b
model_dependency: high | low | none   # Classification criteria in §8
validated_on_models: list[string]     # Accumulated validation successes. First entry matches learned_on_model
excluded_models: list[string]         # Do not use with these models (auto or manual registration after regression/malfunction detection)

# Project/stack scoping (Q3 B strategy)
projects: list[string]                # ["*"] or specific project slugs, e.g. ["my-backend", "hermit-agent"]
languages: list[string]               # ["python", "typescript"]
frameworks: list[string]              # ["django", "fastapi"]
triggers: list[string]                # Retained from existing. Keyword matching for skill selection

# Usage stats (auto-updated)
use_count: int                        # Load/injection count
last_used: "YYYY-MM-DD"
verified: bool                        # pytest pass status (null if no pytest)

# Audit
audience: list[string] (optional)     # ["hermit_agent", "claude-code", "both"] — compatible with HermitAgent loader's existing audience field
---

## Rules
Positive rule + Why (1-3 lines)

## Correct pattern
```code
...
```

## Pattern to avoid
```code
...
```
```

**Frontmatter validator** — Each implementation (CC / HermitAgent) writes its own. Follows this spec's field list.

---

## 5. Lifecycle States

| status | Meaning | Next state | Auto-transition condition |
|---|---|---|---|
| `pending` | Learning detected, not yet verified | `approved` | pytest pass or user approval |
| `approved` | Active. Loader injects it | `needs_review` | 3 use failures or model change + high dep |
| `needs_review` | Awaiting re-verification | `approved` or `deprecated` | Re-verification pass → approved / 30 days unhandled → deprecated |
| `deprecated` | Retired. Loader does not inject | (permanent) | No auto-deletion. Manual recovery possible |
| `auto-learned` | HermitAgent self-learning (skips pending) | `deprecated` | Non-use/failure threshold |

**State is expressed via the `status` field only** (directory location is reference for HermitAgent style, not required — implementation choice).

---

## 6. State Transitions (automatic)

| Event | from | to | Condition |
|---|---|---|---|
| Skill creation (feedback) | — | `pending` | User "don't do this" feedback detected |
| Skill creation (auto) | — | `auto-learned` | Session pattern extraction (same mistake across N turns) |
| Verification pass | `pending` | `approved` | pytest green or user approval |
| Use failure (same skill present yet same mistake repeated) | `approved` | `needs_review` | 3 failures |
| Long-term non-use | `approved` | `deprecated` | 30 days with no `last_used` update |
| Successful use on model | — | — | Append current_model to `validated_on_models` |
| Regression 3 times on model | `approved` | (kept) | Append current_model to `excluded_models`. Also remove from validated |
| Excluded models ≥ 3 | `approved` | `needs_review` | Skill itself is suspect |
| Re-verification success | `needs_review` | `approved` | pytest green or user approval. Update `validated_on_models` |
| Re-verification failure or neglect | `needs_review` | `deprecated` | 30 days unhandled or pytest fail |
| User explicit approval | any | `approved` | Manual command |
| User explicit deprecation | any | `deprecated` | Manual command |

---

## 7. Loader Semantics

When reading skill files, the loader filters using **all conditions ANDed**:

```pseudo
filter(skill):
    if skill.status not in {approved, auto-learned}: skip
    if audience is set and "hermit_agent"|"claude-code"|"both"|... not in audience: skip (existing logic preserved)
    if projects != ["*"] and current_cwd_project not in projects: skip
    if languages is set and current_project_language not in languages: skip
    if frameworks is set and current_project_framework not in frameworks: skip
    (matched → inject)
```

**Current context detection heuristics** (each implementation is responsible):
- `current_project_language`: `pyproject.toml` → python, `package.json` → js/ts, `go.mod` → go, ...
- `current_project_framework`: Dependency inspection (has django → django, has fastapi → fastapi, ...)
- `current_model`: CC from session config, HermitAgent from Gateway `/health` response

---

## 8. Model Version Handling

### Classification criteria (`model_dependency`)

| Value | Meaning | Example | On model change |
|---|---|---|---|
| `high` | Skill addressing a specific model's **tendency/bias/bug** | "Opus 4.6 overuses try/except. Instruct removal" | → auto `needs_review` |
| `low` | Framework/language/domain rule. Partially model-related | "Django 5.0 validator API change" | No change |
| `none` | Fully model-independent | "pytest command path is `poetry run pytest`" | No change |

### Model change detection — Upgrade vs Replacement

**Decision**: Compare the prefix of two model names (up to the first digit or `:`).
- Same prefix → **upgrade**
- Different prefix → **replacement**

```pseudo
def is_upgrade(old, new):
    def prefix(m):
        # "claude-opus-4-6" → "claude-opus"
        # "qwen3-coder:30b" → "qwen3-coder"
        # "glm-5.1"         → "glm"
        m = m.split(":")[0]
        parts = m.split("-")
        return "-".join(p for p in parts if not p[:1].isdigit())
    return prefix(old) == prefix(new)
```

### Load decision — model-swap environment handling

In environments like local LLM setups where **dozens of models are swapped**, full re-validation on every swap is impractical. Use an **accumulated validation** strategy instead.

```pseudo
def should_inject(skill, current_model):
    if current_model in skill.excluded_models:
        return False                              # Determined unusable with this model
    if current_model in skill.validated_on_models:
        return True                               # Already validated, inject immediately
    # First time seeing this model
    if skill.model_dependency == "none":
        return True                               # Model-independent. Inject immediately
    # New model + high/low needs a decision
    any_prefix_match = any(
        is_upgrade(v, current_model)              # Any existing validated model with same prefix (= same line upgrade)
        for v in skill.validated_on_models
    )
    if skill.model_dependency == "low":
        return True                               # low: inject even without prefix match (mostly safe)
    if skill.model_dependency == "high":
        return any_prefix_match                   # high: inject only for same-line upgrades. Skip on replacement.
```

### Validation accumulation (automatic)

```pseudo
on_skill_used_successfully(skill, current_model):
    if current_model not in skill.validated_on_models:
        skill.validated_on_models.append(current_model)
        write(skill)
```

### Regression/malfunction detection → auto-exclude

When a skill exists but the same mistake repeats, it's unsuitable for that model.

```pseudo
on_skill_used_but_same_mistake_repeated(skill, current_model, fail_count):
    if fail_count >= 3:
        if current_model not in skill.excluded_models:
            skill.excluded_models.append(current_model)
        # Also remove from validated list (if present)
        skill.validated_on_models = [m for m in skill.validated_on_models if m != current_model]
        # Too many excluded models → skill itself is suspect
        if len(skill.excluded_models) >= 3:
            skill.status = "needs_review"
        write(skill)
```

### Manual exclude

If a user explicitly says "don't use this skill with qwen3:8b", add it to `excluded_models` immediately.

CC and HermitAgent each maintain their own **"last used model" state file** (e.g.: `~/.claude/state/last_model.txt`, `~/.hermit/state/last_model.txt`).

### Re-verification method

1. **Skill with pytest**: Auto-run → on pass: `last_verified_on_model = current`, status = `approved`
2. **No pytest**: Notify user — "Is this skill still needed? [keep/deprecate]"
3. **30 days no response**: Auto `deprecated`

---

## 9. Auto-deprecation Policies

| Condition | Target | Effect |
|---|---|---|
| `last_used` elapsed ≥ 30 days | `approved` | `deprecated` |
| 3 consecutive failures | `approved` | `needs_review` |
| `needs_review` elapsed ≥ 30 days, unhandled | `needs_review` | `deprecated` |
| `auto-learned` 0 uses, ≥ 14 days since creation | `auto-learned` | `deprecated` |

**Deletion is not automated**. Permanently stored in `deprecated/` → user can recover if needed. Disk footprint is negligible.

---

## 10. Dashboard / Stats (separate per system)

- **HermitAgent**: Existing `_hub_*.md` maintained
- **CC**: New `~/.claude/skills/learned-feedback/_dashboard.md`
  - Sections: Active approved / Needs review / Top 10 recent / Impending deprecation
  - Update: `/cc:learner-stats` command or `session-wrap` hook

Neither reads the other. No synchronization.

---

## 11. Phased Rollout

### Phase 1 — Spec finalization (now)
Review and approve this document. Both implementations reference this spec going forward.

### Phase 2 — CC lifecycle restoration
- Move `~/.claude/skills/learned-feedback/` root flat files → `approved/`
- Backfill required frontmatter fields in each file (existing files default to `model_dependency: low`, `projects: ["*"]`)
- Minimal `~/.claude/scripts/cc-learner.py`: load + filter

### Phase 3 — Auto-transition (both sides)
- `last_used` / `use_count` hook (CC: on load, HermitAgent: already exists)
- 30-day non-use auto-deprecation logic
- Model change detection + move `high` skills to `needs_review`

### Phase 4 — Auto-learned (both sides)
- HermitAgent: Already exists. Only add fields (model/projects/frameworks).
- CC: Extend `session-wrap` skill → pattern extraction via LLM at session end → `auto-learned/`

### Phase 5 — Dashboard & re-verification UI
- HermitAgent: Enhance existing hub
- CC: Generate dashboard + slash command

### Phase 6 — Model manifest
- Track current version per provider (e.g.: `anthropic.opus = 4.7`, `zai.glm = 5.1`)
- Upgrade notifications + auto re-verification trigger

---

## 12. Decided Policies (prev Open Questions)

1. **Model upgrade vs replacement** (decided 2026-04-17)
   - **Upgrade** (version increase within same provider/model line, e.g.: opus 4.6 → 4.7): Only `model_dependency=high` skills → `needs_review`.
   - **Replacement** (provider change or model line change, e.g.: opus → sonnet, glm → qwen): Both `high` and `low` → `needs_review`. Only `none` stays as-is.
   - Decision criteria: String comparison — same prefix before `-`/`:` means upgrade, different means replacement.
     - e.g.: `claude-opus-4-6` → `claude-opus-4-7` = upgrade (prefix `claude-opus-4` matches)
     - e.g.: `claude-opus-4-7` → `claude-sonnet-4-6` = replacement

2. **Project detection failure** — when cwd is not project root
   - Walk upward from cwd to find a directory containing `pyproject.toml` / `package.json` / `go.mod` / `Cargo.toml` as project root.
   - If not found, **skip** project filter (only load skills targeting all projects).

3. **CC self-learning trigger**
   - Only propose skill creation when the same mistake repeats **3+ turns**.
   - `session-wrap` extracts patterns via LLM, saves to `auto-learned/` after user approval.

4. **Keep auto-learned separate** (decided 2026-04-17)
   - Separate `learned-feedback/` (user feedback) vs `auto-learned/` (agent self-learning) directories.
   - Clarity of origin takes priority. Maintainability outweighs logic simplification.

5. **Other provider support (gemini, openai)**
   - `learned_on_model` is just a string. Provider-agnostic, name as-is.
   - Loader handles via §8 prefix match logic.

---

## 13. References

- HermitAgent implementation: `hermit_agent/learner.py` (existing)
- CC implementation: `~/.claude/scripts/cc-learner.py` (planned for Phase 2)
- This spec: Both implementations reference this document. Spec changes require updating both sides simultaneously.

#!/usr/bin/env python3
"""cc-learner — Learning skill lifecycle manager for Claude Code.

Independent implementation: similar interface to HermitAgent's hermit_agent/learner.py but no shared code.

Usage:
    cc-learner.py load                       # list approved/auto-learned skills (filtered)
    cc-learner.py list [--status=approved]   # list by status
    cc-learner.py show <name>                # show skill details
    cc-learner.py touch <name>               # use_count++, update last_used
    cc-learner.py validate <name>            # add current model to validated_on_models
    cc-learner.py exclude <name> <model>     # add to excluded_models
    cc-learner.py sweep                      # auto status transition (30-day unused, etc.)
    cc-learner.py detect-context             # detect language/framework/model of current cwd
    cc-learner.py stats                      # dashboard summary

Directories:
    ~/.claude/skills/learned-feedback/{pending,approved,needs_review,deprecated}/
    ~/.claude/skills/auto-learned/
    ~/.claude/state/last_model.txt           # recently used model record
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

HOME = Path.home()
SKILLS_ROOT = HOME / ".claude/skills"
LF_ROOT = SKILLS_ROOT / "learned-feedback"
AL_ROOT = SKILLS_ROOT / "auto-learned"
STATE_DIR = HOME / ".claude/state"
LAST_MODEL_FILE = STATE_DIR / "last_model.txt"
MODEL_MANIFEST_FILE = STATE_DIR / "model_manifest.json"

# Default latest versions per provider. Fallback when session startup fails to set them.
DEFAULT_MODEL_MANIFEST = {
    "anthropic": {
        "opus": "claude-opus-4-7",
        "sonnet": "claude-sonnet-4-6",
        "haiku": "claude-haiku-4-5",
    },
    "zai": {"glm": "glm-5.1"},
}

STATUS_DIRS = {
    "pending": LF_ROOT / "pending",
    "approved": LF_ROOT / "approved",
    "needs_review": LF_ROOT / "needs_review",
    "deprecated": LF_ROOT / "deprecated",
}

UNUSED_DAYS = 30
NEEDS_REVIEW_DAYS = 30
FAIL_THRESHOLD = 3
EXCLUDED_THRESHOLD = 3


def _ensure_dirs() -> None:
    for d in STATUS_DIRS.values():
        d.mkdir(parents=True, exist_ok=True)
    AL_ROOT.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _now_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ─── Frontmatter parsing (simple YAML subset) ─────────────────────────────────────

_FM_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def _parse_list(value: str) -> list[str]:
    """'[a, b, "c"]' → ['a','b','c']"""
    s = value.strip()
    if not (s.startswith("[") and s.endswith("]")):
        return []
    inner = s[1:-1].strip()
    if not inner:
        return []
    return [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]


def _dump_list(items: list[str]) -> str:
    return "[" + ", ".join(f'"{x}"' for x in items) + "]"


@dataclass
class Skill:
    path: Path
    meta: dict[str, Any] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    body: str = ""

    @property
    def name(self) -> str:
        return str(self.meta.get("name", self.path.stem))

    @property
    def status(self) -> str:
        return str(self.meta.get("status", "approved"))

    @property
    def validated_on_models(self) -> list[str]:
        return _parse_list(str(self.meta.get("validated_on_models", "[]")))

    @property
    def excluded_models(self) -> list[str]:
        return _parse_list(str(self.meta.get("excluded_models", "[]")))

    @property
    def projects(self) -> list[str]:
        return _parse_list(str(self.meta.get("projects", '["*"]')))

    @property
    def frameworks(self) -> list[str]:
        return _parse_list(str(self.meta.get("frameworks", "[]")))

    @property
    def languages(self) -> list[str]:
        return _parse_list(str(self.meta.get("languages", "[]")))

    @property
    def model_dependency(self) -> str:
        return str(self.meta.get("model_dependency", "low"))

    @property
    def use_count(self) -> int:
        try:
            return int(self.meta.get("use_count", 0))
        except Exception:
            return 0

    @property
    def last_used(self) -> str:
        return str(self.meta.get("last_used", "")).strip('"')

    def set(self, key: str, value: Any) -> None:
        if key not in self.order:
            self.order.append(key)
        if isinstance(value, list):
            self.meta[key] = _dump_list(value)
        elif isinstance(value, bool):
            self.meta[key] = "true" if value else "false"
        elif value is None:
            self.meta[key] = "null"
        else:
            self.meta[key] = str(value)

    def write(self) -> None:
        lines = [f"{k}: {self.meta[k]}" for k in self.order if k in self.meta]
        text = "---\n" + "\n".join(lines) + "\n---\n" + self.body
        self.path.write_text(text)


def load_skill(path: Path) -> Skill | None:
    try:
        text = path.read_text()
    except Exception:
        return None
    m = _FM_RE.match(text)
    if not m:
        return None
    fm_raw, body = m.group(1), m.group(2)
    meta: dict[str, Any] = {}
    order: list[str] = []
    for line in fm_raw.splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-")):
            k, _, v = line.partition(":")
            k = k.strip()
            meta[k] = v.strip()
            order.append(k)
    return Skill(path=path, meta=meta, order=order, body=body)


def iter_skills(status: str | None = None) -> list[Skill]:
    _ensure_dirs()
    skills: list[Skill] = []
    targets: list[Path] = []
    if status and status in STATUS_DIRS:
        targets.append(STATUS_DIRS[status])
    elif status == "auto-learned":
        targets.append(AL_ROOT)
    elif status is None:
        targets.extend(STATUS_DIRS.values())
        targets.append(AL_ROOT)
    else:
        return []
    for d in targets:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            if p.name.startswith("_"):
                continue
            s = load_skill(p)
            if s:
                skills.append(s)
    return skills


# ─── Context detection ──────────────────────────────────────────────────────────


def detect_project_root(cwd: Path) -> Path | None:
    markers = ("pyproject.toml", "package.json", "go.mod", "Cargo.toml")
    cur = cwd.resolve()
    for _ in range(20):
        if any((cur / m).exists() for m in markers):
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def detect_language(root: Path | None) -> list[str]:
    if not root:
        return []
    langs = []
    if (root / "pyproject.toml").exists():
        langs.append("python")
    if (root / "package.json").exists():
        langs.append("typescript")  # JS/TS treated as one category
    if (root / "go.mod").exists():
        langs.append("go")
    if (root / "Cargo.toml").exists():
        langs.append("rust")
    return langs


def detect_framework(root: Path | None) -> list[str]:
    if not root:
        return []
    fw = []
    py = root / "pyproject.toml"
    if py.exists():
        text = py.read_text()
        if "django" in text.lower():
            fw.append("django")
        if "fastapi" in text.lower():
            fw.append("fastapi")
        if "pytest" in text.lower():
            fw.append("pytest")
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "react" in deps:
                fw.append("react")
            if "next" in deps:
                fw.append("nextjs")
            if "vitest" in deps:
                fw.append("vitest")
            if "jest" in deps:
                fw.append("jest")
        except Exception:
            pass
    return fw


def current_model() -> str:
    if LAST_MODEL_FILE.exists():
        return LAST_MODEL_FILE.read_text().strip()
    return ""


def update_current_model(model: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LAST_MODEL_FILE.write_text(model.strip())


def detect_context(cwd: Path | None = None) -> dict[str, Any]:
    cwd = cwd or Path.cwd()
    root = detect_project_root(cwd)
    return {
        "cwd": str(cwd),
        "project_root": str(root) if root else None,
        "project_name": root.name if root else None,
        "languages": detect_language(root),
        "frameworks": detect_framework(root),
        "current_model": current_model(),
    }


# ─── Upgrade vs replacement ─────────────────────────────────────────────────────


def _model_prefix(m: str) -> str:
    """'claude-opus-4-7' → 'claude-opus'. 'qwen3-coder:30b' → 'qwen3-coder'."""
    m = (m or "").split(":")[0]
    parts = m.split("-")
    # drop parts that look like version digits
    keep = [p for p in parts if not (p and p[0].isdigit())]
    return "-".join(keep)


def is_upgrade(old: str, new: str) -> bool:
    if not old or not new:
        return False
    return _model_prefix(old) == _model_prefix(new)


# ─── Loader filter ──────────────────────────────────────────────────────────────


def should_inject(skill: Skill, ctx: dict[str, Any]) -> bool:
    if skill.status not in ("approved", "auto-learned"):
        return False

    # projects
    projects = skill.projects
    if projects and projects != ["*"]:
        if ctx.get("project_name") not in projects:
            return False

    # languages
    langs = skill.languages
    if langs:
        if not any(l in ctx.get("languages", []) for l in langs):
            return False

    # frameworks
    fws = skill.frameworks
    if fws and fws != ["none"]:
        if not any(f in ctx.get("frameworks", []) for f in fws):
            return False

    # model gating
    cur = ctx.get("current_model", "")
    if cur:
        if cur in skill.excluded_models:
            return False
        if cur in skill.validated_on_models:
            return True
        # unseen model
        dep = skill.model_dependency
        if dep == "none":
            return True
        if dep == "low":
            return True
        # high: only if same prefix exists in validated list
        if dep == "high":
            return any(is_upgrade(v, cur) for v in skill.validated_on_models)
    return True


# ─── Commands ───────────────────────────────────────────────────────────────────


def cmd_load(args: argparse.Namespace) -> None:
    ctx = detect_context()
    injected: list[Skill] = []
    for s in iter_skills(status="approved") + iter_skills(status="auto-learned"):
        if should_inject(s, ctx):
            injected.append(s)
    if args.format == "json":
        print(json.dumps([{"name": s.name, "path": str(s.path), "description": s.meta.get("description", "")} for s in injected], ensure_ascii=False, indent=2))
    else:
        for s in injected:
            print(f"{s.name}\t[{s.path.parent.name}]\t{s.meta.get('description', '')}")


def cmd_list(args: argparse.Namespace) -> None:
    for s in iter_skills(status=args.status):
        loc = s.path.parent.name
        print(f"[{loc}] {s.name} — {s.meta.get('description', '')}")


def cmd_show(args: argparse.Namespace) -> None:
    for s in iter_skills():
        if s.path.stem == args.name or s.name == args.name:
            print(s.path.read_text())
            return
    print(f"skill not found: {args.name}", file=sys.stderr)
    sys.exit(1)


def _find_skill(name: str) -> Skill | None:
    for s in iter_skills():
        if s.path.stem == name or s.name == name:
            return s
    return None


def cmd_touch(args: argparse.Namespace) -> None:
    s = _find_skill(args.name)
    if not s:
        print(f"not found: {args.name}", file=sys.stderr)
        sys.exit(1)
    s.set("use_count", s.use_count + 1)
    s.set("last_used", _now_date())
    s.write()
    print(f"updated: {s.name} use_count={s.use_count} last_used={s.last_used}")


def cmd_validate(args: argparse.Namespace) -> None:
    s = _find_skill(args.name)
    if not s:
        print(f"not found: {args.name}", file=sys.stderr)
        sys.exit(1)
    model = args.model or current_model()
    if not model:
        print("no model given and no last_model.txt", file=sys.stderr)
        sys.exit(1)
    vals = s.validated_on_models
    if model not in vals:
        vals.append(model)
        s.set("validated_on_models", vals)
    # remove from excluded if present
    excl = [m for m in s.excluded_models if m != model]
    s.set("excluded_models", excl)
    s.write()
    print(f"validated: {s.name} on {model}")


def cmd_exclude(args: argparse.Namespace) -> None:
    s = _find_skill(args.name)
    if not s:
        print(f"not found: {args.name}", file=sys.stderr)
        sys.exit(1)
    model = args.model
    excl = s.excluded_models
    if model not in excl:
        excl.append(model)
        s.set("excluded_models", excl)
    vals = [m for m in s.validated_on_models if m != model]
    s.set("validated_on_models", vals)
    if len(excl) >= EXCLUDED_THRESHOLD and s.status == "approved":
        _move(s, "needs_review")
    else:
        s.write()
    print(f"excluded: {s.name} on {model} (total excluded: {len(excl)})")


def _move(s: Skill, new_status: str) -> None:
    s.set("status", new_status)
    dst_dir = STATUS_DIRS.get(new_status, LF_ROOT / new_status)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / s.path.name
    old_path = s.path
    s.path = dst
    s.write()
    if old_path.exists() and old_path != dst:
        old_path.unlink()


def _model_change_requires_review(skill: Skill, current: str) -> bool:
    """Determine whether this skill needs review for the current model.

    - If already in validated_on_models or excluded_models → already handled → False
    - none: no impact → False
    - high: prefix differs from all validated (replacement) → True
    - high: even if upgrade (same prefix) → True (re-validate once)
    - low: only on replacement → True. Skip on upgrade
    """
    if not current:
        return False
    if current in skill.validated_on_models or current in skill.excluded_models:
        return False
    dep = skill.model_dependency
    if dep == "none":
        return False
    # Determine: if any validated entry has the same prefix, it's an "upgrade"
    has_same_line = any(is_upgrade(v, current) for v in skill.validated_on_models)
    if dep == "high":
        # re-validate on both upgrade and replacement
        return True
    if dep == "low":
        # auto-allow on upgrade, re-validate on replacement
        return not has_same_line
    return False


def cmd_sweep(_args: argparse.Namespace) -> None:
    """Auto status transitions:
    - approved unused for 30 days → deprecated
    - needs_review stale for 30 days → deprecated
    - new model detected → approved → needs_review based on model_dependency
    """
    now = datetime.now()
    current = current_model()
    changed = 0
    for s in iter_skills():
        try:
            last = datetime.strptime(s.last_used, "%Y-%m-%d") if s.last_used else None
        except Exception:
            last = None
        if s.status == "approved":
            if last and (now - last) > timedelta(days=UNUSED_DAYS) and s.use_count > 0:
                _move(s, "deprecated")
                changed += 1
                print(f"→ deprecated (unused {UNUSED_DAYS}d): {s.name}")
                continue
            if current and _model_change_requires_review(s, current):
                _move(s, "needs_review")
                changed += 1
                reason = "high dep" if s.model_dependency == "high" else "low dep + replacement"
                print(f"→ needs_review (model change: {current}, {reason}): {s.name}")
                continue
        elif s.status == "needs_review":
            # Use file mtime as a proxy (no dedicated field for entry timestamp)
            mtime = datetime.fromtimestamp(s.path.stat().st_mtime)
            if (now - mtime) > timedelta(days=NEEDS_REVIEW_DAYS):
                _move(s, "deprecated")
                changed += 1
                print(f"→ deprecated (needs_review stale {NEEDS_REVIEW_DAYS}d): {s.name}")
    if changed == 0:
        print("nothing swept.")


def cmd_detect_context(_args: argparse.Namespace) -> None:
    print(json.dumps(detect_context(), ensure_ascii=False, indent=2))


def _stats_data() -> dict[str, Any]:
    skills = iter_skills()
    counts: dict[str, int] = {}
    for s in skills:
        counts[s.status] = counts.get(s.status, 0) + 1
    sorted_used = sorted((s for s in skills if s.use_count > 0), key=lambda s: -s.use_count)[:10]
    # Approaching deprecation (approved + 20+ days unused)
    now = datetime.now()
    dep_risk = []
    for s in skills:
        if s.status != "approved" or not s.last_used:
            continue
        try:
            last = datetime.strptime(s.last_used, "%Y-%m-%d")
        except Exception:
            continue
        days = (now - last).days
        if days >= 20:
            dep_risk.append((days, s))
    dep_risk.sort(key=lambda x: -x[0])
    # Pending needs_review
    nr = [s for s in skills if s.status == "needs_review"]
    # Skills with excluded_models
    excluded = [s for s in skills if s.excluded_models]
    return {
        "total": len(skills),
        "counts": counts,
        "top_used": sorted_used,
        "dep_risk": dep_risk,
        "needs_review": nr,
        "excluded_any": excluded,
        "current_model": current_model(),
    }


def cmd_stats(_args: argparse.Namespace) -> None:
    d = _stats_data()
    print(f"Total: {d['total']}")
    for k in ("approved", "auto-learned", "pending", "needs_review", "deprecated"):
        print(f"  {k:<14} {d['counts'].get(k, 0)}")
    print(f"\ncurrent_model: {d['current_model'] or '(none)'}")
    if d["top_used"]:
        print("\nTop used:")
        for s in d["top_used"]:
            print(f"  {s.use_count:>4}  {s.name}")
    if d["needs_review"]:
        print(f"\nneeds_review ({len(d['needs_review'])}):")
        for s in d["needs_review"]:
            print(f"  - {s.name}")
    if d["dep_risk"]:
        print("\nDeprecation risk (20+ days unused):")
        for days, s in d["dep_risk"][:5]:
            print(f"  {days}d  {s.name}")


def cmd_dashboard(_args: argparse.Namespace) -> None:
    """Generate _dashboard.md — saved to the learned-feedback directory root."""
    d = _stats_data()
    lines = [
        "# CC Learned Feedback Dashboard",
        "",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        f"_current_model: {d['current_model'] or '(none)'}_",
        "",
        "## Summary",
        f"- Total skills: **{d['total']}**",
    ]
    for k in ("approved", "auto-learned", "pending", "needs_review", "deprecated"):
        lines.append(f"- {k}: {d['counts'].get(k, 0)}")

    if d["top_used"]:
        lines.append("\n## Top Used")
        lines.append("| use_count | name |")
        lines.append("|----------:|------|")
        for s in d["top_used"]:
            lines.append(f"| {s.use_count} | {s.name} |")

    if d["needs_review"]:
        lines.append(f"\n## Needs Review ({len(d['needs_review'])})")
        for s in d["needs_review"]:
            lines.append(f"- `{s.path.name}` — {s.name}")

    if d["dep_risk"]:
        lines.append("\n## Deprecation Risk (20+ days unused)")
        lines.append("| days | name |")
        lines.append("|-----:|------|")
        for days, s in d["dep_risk"][:20]:
            lines.append(f"| {days} | {s.name} |")

    if d["excluded_any"]:
        lines.append(f"\n## Skills with Excluded Models ({len(d['excluded_any'])})")
        for s in d["excluded_any"]:
            lines.append(f"- `{s.name}` — excluded: {', '.join(s.excluded_models)}")

    lines.append("\n---\n_Update: `cc-learner dashboard`_")

    out = LF_ROOT / "_dashboard.md"
    out.write_text("\n".join(lines))
    print(f"dashboard written: {out}")


def load_manifest() -> dict[str, dict[str, str]]:
    if MODEL_MANIFEST_FILE.exists():
        try:
            return json.loads(MODEL_MANIFEST_FILE.read_text())
        except Exception:
            pass
    return DEFAULT_MODEL_MANIFEST


def save_manifest(data: dict[str, dict[str, str]]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_MANIFEST_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_set_model(args: argparse.Namespace) -> None:
    update_current_model(args.model)
    print(f"current_model = {args.model}")


_DAILY_GUIDE = """\
# cc-learner — daily usage guide

## Daily start
  cc-learner sweep                              # auto status transitions (30d unused → deprecated, model change → needs_review)
  cc-learner dashboard                          # update _dashboard.md
  cc-learner stats                              # console summary

## Skill usage feedback
  cc-learner validate <skill_name>              # record that it works well on the current model
  cc-learner validate <skill_name> --model M    # specify a particular model
  cc-learner exclude <skill_name> <model>       # do not use on this model
  cc-learner touch <skill_name>                 # increment use_count + update last_used

## Loading / search
  cc-learner load                               # skill list matching current context (filter applied)
  cc-learner load --format json                 # JSON output (script integration)
  cc-learner list --status approved             # list by status
  cc-learner show <skill_name>                  # print skill content
  cc-learner detect-context                     # show detected language/framework/model

## Model management
  cc-learner set-model claude-opus-4-7          # record current model (referenced by sweep/load)
  cc-learner manifest show                      # per-provider 'latest model' manifest
  cc-learner manifest set anthropic opus claude-opus-4-8
  cc-learner manifest reset                     # reset to defaults

## Learning generation (used by session-wrap, etc.)
  echo "## Rules\\n..." | cc-learner auto-learn \\
      --name "api_no_trailing_slash" \\
      --description "Do not add trailing slash to API" \\
      --languages python --frameworks django \\
      --model-dependency low

## Delegate learning extraction to HermitAgent (CC token savings)
  # 1. Save conversation transcript, then generate HermitAgent directive via delegate-prompt
  cc-learner delegate-prompt --transcript /tmp/cc-transcript.txt
  # 2. CC delegates this prompt via mcp__hermit__run_task(task=..., background=true)
  # 3. HermitAgent returns YAML → CC parses + makes final judgment, then
  #    saves each item via cc-learner auto-learn or kb-wiki

## Common combos
  Daily:    cc-learner sweep && cc-learner dashboard
  New model: cc-learner set-model <model> && cc-learner sweep
  Regression found: cc-learner exclude <skill> <model>
  Validation success: cc-learner validate <skill>

## Directories
  ~/.claude/skills/learned-feedback/{pending,approved,needs_review,deprecated}/
  ~/.claude/skills/auto-learned/
  ~/.claude/state/last_model.txt                # current model
  ~/.claude/state/model_manifest.json           # provider manifest

## Reference
  spec: .dev/learner-spec.md
  repo backup: scripts/harness/cc-learner.py
"""


def cmd_help(_args: argparse.Namespace) -> None:
    print(_DAILY_GUIDE)


def cmd_manifest(args: argparse.Namespace) -> None:
    """Query/set per-provider 'latest model' info.

    Usage:
      cc-learner manifest              → show current manifest
      cc-learner manifest set anthropic opus claude-opus-4-8
      cc-learner manifest reset        → restore to DEFAULT_MODEL_MANIFEST
    """
    sub = args.action
    manifest = load_manifest()
    if sub == "show" or sub is None:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    elif sub == "set":
        if not (args.provider and args.line and args.model):
            print("usage: manifest set <provider> <line> <model>", file=sys.stderr)
            sys.exit(1)
        manifest.setdefault(args.provider, {})[args.line] = args.model
        save_manifest(manifest)
        print(f"set {args.provider}.{args.line} = {args.model}")
    elif sub == "reset":
        save_manifest(DEFAULT_MODEL_MANIFEST)
        print("manifest reset to default")
    else:
        print(f"unknown action: {sub}", file=sys.stderr)
        sys.exit(1)


_DELEGATE_PROMPT_TEMPLATE = """\
You are HermitAgent. Extract learnable items from the CC session transcript below.

Transcript path: {transcript_path}

Output strict YAML with TWO top-level keys:

behavioral_rules:
  # Behavioral norms (target: ~/.claude/skills/auto-learned/). "Do not ...", "When ..., ..." form.
  - name: string (snake_case)
    description: 1-line summary
    rule: the rule itself (positive form)
    why: 1-2 sentences
    model_dependency: high | low | none
    languages: [python, typescript, ...]
    frameworks: [django, fastapi, ...]
    projects: ["*"] or ["specific-project"]

domain_facts:
  # Domain knowledge (target: kb/wiki/). Facts, definitions, flows, external API specs, state transitions.
  - title: string
    domain: glossary | flow | external_api | state_machine | incident | adr
    fact: the fact itself
    confidence: 0.5-1.0
    tags: [...]

Filtering rules (strict):
- Only items that RECUR or are EXPLICITLY stated by the user. Single offhand mentions → ignore.
- Implementation details that the CODE answers → NOT domain_facts.
- Bug fixes where commit msg is the answer → NOT behavioral_rules.
- "Just this once" temperament → exclude from both piles.

Return ONLY the YAML. No markdown fence. No commentary.
"""


def cmd_delegate_prompt(args: argparse.Namespace) -> None:
    """Print a 'learning extraction' prompt for HermitAgent to stdout.

    CC takes this output and delegates via `mcp__hermit__run_task(task=prompt, cwd=..., background=true)`.
    CC parses HermitAgent's YAML result, makes a final judgment, and saves via cc-learner auto-learn.

    This command itself does not call an LLM. It only generates a prompt template.
    """
    transcript_path = args.transcript or "(pass transcript file path to HermitAgent's read_file)"
    print(_DELEGATE_PROMPT_TEMPLATE.format(transcript_path=transcript_path))


def cmd_auto_learn(args: argparse.Namespace) -> None:
    """Save patterns extracted by the LLM during a session to auto-learned/.

    Actual pattern extraction is performed by the session-wrap skill (or CC itself),
    and this command only creates the skill file.

    Receive the skill body via stdin, or specify --body/--from-file.
    Frontmatter fields are passed via --name --description --frameworks --languages --projects --model-dependency.
    """
    if args.from_file:
        body = Path(args.from_file).read_text()
    elif args.body:
        body = args.body
    else:
        body = sys.stdin.read()
    if not body.strip():
        print("empty body", file=sys.stderr)
        sys.exit(1)

    # Determine whether frontmatter is present
    if body.lstrip().startswith("---"):
        # Already contains frontmatter — save as-is
        text = body
    else:
        now = _now_date()
        model = current_model() or "unknown"
        lines = [
            f"name: {args.name}",
            f"description: {args.description or ''}",
            "type: auto-learned",
            "status: auto-learned",
            f"learned_from: {now} + session auto-extraction",
            f"learned_on_model: {model}",
            f"model_dependency: {args.model_dependency or 'low'}",
            f"frameworks: {_dump_list(args.frameworks or [])}",
            f"languages: {_dump_list(args.languages or [])}",
            f"projects: {_dump_list(args.projects or ['*'])}",
            "use_count: 0",
            'last_used: ""',
            "verified: null",
            f"validated_on_models: {_dump_list([model] if model != 'unknown' else [])}",
            "excluded_models: []",
        ]
        text = "---\n" + "\n".join(lines) + "\n---\n" + body

    # slug
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", args.name).strip("_").lower() or "auto"
    dst = AL_ROOT / f"{slug}.md"
    if dst.exists() and not args.overwrite:
        print(f"exists (use --overwrite): {dst}", file=sys.stderr)
        sys.exit(1)
    AL_ROOT.mkdir(parents=True, exist_ok=True)
    dst.write_text(text)
    print(f"saved: {dst}")


# ─── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(prog="cc-learner")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("help", help="show daily usage guide (example commands)")
    p.set_defaults(func=cmd_help)

    p = sub.add_parser("load", help="list skills that should be injected given current context")
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.set_defaults(func=cmd_load)

    p = sub.add_parser("list", help="list skills (optionally by status)")
    p.add_argument("--status", default=None, choices=list(STATUS_DIRS.keys()) + ["auto-learned"])
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="print skill content")
    p.add_argument("name")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("touch", help="bump use_count + last_used")
    p.add_argument("name")
    p.set_defaults(func=cmd_touch)

    p = sub.add_parser("validate", help="add current model (or --model) to validated_on_models")
    p.add_argument("name")
    p.add_argument("--model", default=None)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("exclude", help="add model to excluded_models")
    p.add_argument("name")
    p.add_argument("model")
    p.set_defaults(func=cmd_exclude)

    p = sub.add_parser("sweep", help="auto-transition stale skills")
    p.set_defaults(func=cmd_sweep)

    p = sub.add_parser("detect-context", help="detect cwd language/framework/model")
    p.set_defaults(func=cmd_detect_context)

    p = sub.add_parser("stats", help="portfolio stats")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("dashboard", help="write _dashboard.md with portfolio summary")
    p.set_defaults(func=cmd_dashboard)

    p = sub.add_parser("set-model", help="record current model (written to state/last_model.txt)")
    p.add_argument("model")
    p.set_defaults(func=cmd_set_model)

    p = sub.add_parser("manifest", help="manage model manifest (provider → latest)")
    p.add_argument("action", nargs="?", choices=["show", "set", "reset"], default="show")
    p.add_argument("provider", nargs="?", default=None)
    p.add_argument("line", nargs="?", default=None)
    p.add_argument("model", nargs="?", default=None)
    p.set_defaults(func=cmd_manifest)

    p = sub.add_parser("delegate-prompt", help="Print prompt to delegate learning extraction to HermitAgent")
    p.add_argument("--transcript", default=None, help="Conversation transcript file path (HermitAgent reads via read_file)")
    p.set_defaults(func=cmd_delegate_prompt)

    p = sub.add_parser("auto-learn", help="save a new auto-learned skill (body from stdin or --body)")
    p.add_argument("--name", required=True, help="human-readable name")
    p.add_argument("--description", default="")
    p.add_argument("--model-dependency", default="low", choices=["high", "low", "none"])
    p.add_argument("--frameworks", nargs="*", default=None)
    p.add_argument("--languages", nargs="*", default=None)
    p.add_argument("--projects", nargs="*", default=None)
    p.add_argument("--body", default=None)
    p.add_argument("--from-file", default=None)
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_auto_learn)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()

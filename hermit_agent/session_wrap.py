"""Session wrap — generates and saves a handoff artifact on session end.

Same purpose as Claude Code's `session-wrap` skill: leaves a markdown file with
summary + file changes + next steps so the following session can reconstruct context.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


_HANDOFF_DIR_NAME = os.path.join(".hermit", "handoffs")


def build_handoff(
    summary: str,
    files_touched: list[str],
    next_steps: list[str],
) -> str:
    """Render 3-section markdown — Summary / Files / Next Steps."""
    lines = [
        f"# Session Handoff — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        summary.strip() or "(none)",
        "",
        "## Files",
    ]
    if files_touched:
        lines.extend(f"- {f}" for f in files_touched)
    else:
        lines.append("_(none recorded)_")
    lines.append("")
    lines.append("## Next Steps")
    if next_steps:
        lines.extend(f"- {s}" for s in next_steps)
    else:
        lines.append("_(none recorded)_")
    lines.append("")
    return "\n".join(lines)


def save_handoff(
    content: str,
    session_id: str | None = None,
    cwd: str | None = None,
) -> Path:
    cwd = cwd or os.getcwd()
    handoffs_dir = Path(cwd) / _HANDOFF_DIR_NAME
    handoffs_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{ts}_{session_id}.md" if session_id else f"{ts}.md"
    path = handoffs_dir / filename
    path.write_text(content)
    return path


_TRUTHY = {"1", "true", "yes", "on"}


def maybe_auto_wrap(
    cwd: str,
    session_id: str | None,
    modified_files: list[str],
) -> Path | None:
    """Conditionally save an automatic handoff on shutdown.

    Activation conditions:
    - Only when `HERMIT_AUTO_WRAP` env is a truthy value ({"1","true","yes","on"})
    - Skipped if modified_files is empty (prevents empty handoffs)
    """
    if os.environ.get("HERMIT_AUTO_WRAP", "").lower() not in _TRUTHY:
        return None
    if not modified_files:
        return None
    summary = f"Auto-wrap on shutdown — {len(modified_files)} file(s) changed."
    content = build_handoff(
        summary=summary,
        files_touched=sorted(modified_files),
        next_steps=[],
    )
    return save_handoff(content=content, session_id=session_id, cwd=cwd)

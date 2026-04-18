"""PRD (Product Requirements Document) system.

prd.json file management: stories + acceptance criteria.
Extract stories from interview spec or user requests.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, field


@dataclass
class Story:
    id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    priority: int = 1  # 1=high, 2=medium, 3=low
    passes: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "acceptance_criteria": self.acceptance_criteria,
            "priority": self.priority,
            "passes": self.passes,
        }

    @staticmethod
    def from_dict(d: dict) -> Story:
        return Story(
            id=d["id"],
            title=d["title"],
            description=d.get("description", ""),
            acceptance_criteria=d.get("acceptance_criteria", []),
            priority=d.get("priority", 1),
            passes=d.get("passes", False),
        )


@dataclass
class PRD:
    title: str
    description: str
    stories: list[Story] = field(default_factory=list)
    created_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "stories": [s.to_dict() for s in self.stories],
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(d: dict) -> PRD:
        prd = PRD(
            title=d.get("title", ""),
            description=d.get("description", ""),
            created_at=d.get("created_at", 0.0),
        )
        prd.stories = [Story.from_dict(s) for s in d.get("stories", [])]
        return prd

    @property
    def pending_stories(self) -> list[Story]:
        return [s for s in self.stories if not s.passes]

    @property
    def completed_stories(self) -> list[Story]:
        return [s for s in self.stories if s.passes]

    @property
    def is_complete(self) -> bool:
        return bool(self.stories) and all(s.passes for s in self.stories)


PRD_DIR = os.path.expanduser("~/.hermit/prd")


def save_prd(prd: PRD, path: str | None = None) -> str:
    """Save PRD to JSON file. Use default path if no path is provided."""
    os.makedirs(PRD_DIR, exist_ok=True)
    if path is None:
        slug = re.sub(r"[^a-zA-Z0-9]", "-", prd.title[:30].lower()).strip("-") or "prd"
        path = os.path.join(PRD_DIR, f"{slug}.json")
    with open(path, "w") as f:
        json.dump(prd.to_dict(), f, ensure_ascii=False, indent=2)
    return path


def load_prd(path: str) -> PRD | None:
    """Load PRD from JSON file."""
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return PRD.from_dict(json.load(f))
    except Exception:
        return None


def load_latest_prd() -> PRD | None:
    """Load the most recently modified PRD."""
    if not os.path.exists(PRD_DIR):
        return None
    files = sorted(
        [f for f in os.listdir(PRD_DIR) if f.endswith(".json")],
        key=lambda f: os.path.getmtime(os.path.join(PRD_DIR, f)),
        reverse=True,
    )
    if not files:
        return None
    return load_prd(os.path.join(PRD_DIR, files[0]))


def update_story(prd: PRD, story_id: str, passes: bool, prd_path: str | None = None) -> bool:
    """Update the passes status of a specific story. Return True after saving."""
    for story in prd.stories:
        if story.id == story_id:
            story.passes = passes
            save_prd(prd, prd_path)
            return True
    return False


# ─── Generate PRD ──────────────────────────────────────────────

def generate_prd_from_spec(llm, spec: str, title: str = "") -> PRD:
    """Extract PRD stories from interview spec using LLM."""
    import time

    prompt = f"""Extract user stories from this specification.

Spec:
{spec}

Return ONLY a JSON object in this exact format:
{{
  "title": "short project title",
  "description": "1-2 sentence project description",
  "stories": [
    {{
      "title": "story title",
      "description": "what and why",
      "acceptance_criteria": ["criterion 1", "criterion 2", "criterion 3"],
      "priority": 1
    }}
  ]
}}

Rules:
- 3-7 stories, ordered by priority (1=highest)
- Each story has 2-5 testable acceptance criteria
- Stories should be independently implementable
- priority: 1=must have, 2=should have, 3=nice to have"""

    try:
        response = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="You extract user stories from specifications. Return ONLY valid JSON.",
            temperature=0.1,
        )
        text = response.content or "{}"
        # Extract JSON
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            data = json.loads(text[start:end])
            prd = PRD(
                title=title or data.get("title", "Project"),
                description=data.get("description", spec[:200]),
                created_at=time.time(),
            )
            for i, s in enumerate(data.get("stories", [])[:7]):
                prd.stories.append(Story(
                    id=uuid.uuid4().hex[:8],
                    title=s.get("title", f"Story {i+1}"),
                    description=s.get("description", ""),
                    acceptance_criteria=s.get("acceptance_criteria", []),
                    priority=s.get("priority", 1),
                    passes=False,
                ))
            return prd
    except Exception:
        pass

    # Fallback: single story
    import time as _time
    return PRD(
        title=title or "Project",
        description=spec[:200],
        stories=[Story(
            id=uuid.uuid4().hex[:8],
            title="Implement the feature",
            description=spec[:500],
            acceptance_criteria=["Feature is implemented and working"],
            priority=1,
            passes=False,
        )],
        created_at=_time.time(),
    )

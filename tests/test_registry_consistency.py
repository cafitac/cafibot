"""Verify registry.yaml key format.

The previous cross-check against docs/archive/cc-behavior-research.md was
removed together with that internal research document; only the format
invariant survives here because it is what production code relies on.
"""

import re
from pathlib import Path


def _load_registry_keys() -> set[str]:
    """Return the list of top-level G# keys from registry.yaml."""
    import yaml
    registry_path = Path(__file__).parent.parent / "hermit_agent" / "guardrails" / "registry.yaml"
    with open(registry_path) as f:
        data = yaml.safe_load(f) or {}
    return set(data.keys())


def test_registry_gids_are_valid_format():
    """Verify that registry keys follow the G<number> or G<number>+<letter> format."""
    registry_keys = _load_registry_keys()
    invalid = [k for k in registry_keys if not re.match(r"G\d+[a-zA-Z]?$", k)]
    assert not invalid, f"Invalid registry key format: {invalid}"

"""VERIFIER prompt strictness tuning + parse_verdict helper.

Changes:
- Specify "RUN tests, not just suggest" in VERIFIER_SYSTEM_PROMPT
- Require `VERDICT:` on the first line in VERIFIER_PROMPT + evidence section
- parse_verdict() extracts PASS/FAIL/UNKNOWN from verifier output

Red-Green:
1. No parse_verdict → Red
2. Implementation + prompt update → Green
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.auto_agents import (
    VERIFIER_PROMPT,
    VERIFIER_SYSTEM_PROMPT,
    parse_verdict,
)


def test_system_prompt_requires_actual_execution():
    """The System prompt must require actual execution, not just suggestions."""
    s = VERIFIER_SYSTEM_PROMPT.lower()
    assert "run" in s
    assert "bash" in s or "execute" in s
    # It should not only have "suggest" without an expression forcing execution.
    assert "do not assume" in s or "actually" in s


def test_prompt_template_has_verdict_line():
    """The Task prompt must specify the VERDICT: first line format."""
    assert "VERDICT:" in VERIFIER_PROMPT
    assert "{task_description}" in VERIFIER_PROMPT


def test_prompt_template_has_evidence_slot():
    assert "evidence" in VERIFIER_PROMPT.lower()


def test_parse_verdict_pass():
    output = "VERDICT: PASS\nAll tests passed, no syntax errors."
    assert parse_verdict(output) == "PASS"


def test_parse_verdict_fail():
    output = "VERDICT: FAIL\n- Test test_x failed: ImportError"
    assert parse_verdict(output) == "FAIL"


def test_parse_verdict_case_insensitive():
    assert parse_verdict("verdict: pass") == "PASS"
    assert parse_verdict("Verdict: Fail") == "FAIL"


def test_parse_verdict_finds_on_any_line():
    """Extract VERDICT: if present, even if it is not on the first line."""
    output = "Some preamble\nHere's analysis\nVERDICT: PASS\ntrailing"
    assert parse_verdict(output) == "PASS"


def test_parse_verdict_unknown_when_absent():
    assert parse_verdict("no verdict here") == "UNKNOWN"


def test_parse_verdict_unknown_when_invalid_label():
    assert parse_verdict("VERDICT: maybe") == "UNKNOWN"


def test_parse_verdict_empty_input():
    assert parse_verdict("") == "UNKNOWN"

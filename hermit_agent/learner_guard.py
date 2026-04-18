"""learner_guard — security scan for self-learned skills.

Based on core patterns from hermes-agent/tools/skills_guard.py (exfiltration, injection, destructive).
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# detection patterns (pattern, label, description)
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # environment variable exfiltration
    (
        re.compile(r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)\b', re.IGNORECASE),
        "env_exfil_curl",
        "curl command interpolates secret env var — exfiltration risk",
    ),
    (
        re.compile(r'wget\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD)\b', re.IGNORECASE),
        "env_exfil_wget",
        "wget command interpolates secret env var — exfiltration risk",
    ),
    # reading secret files
    (
        re.compile(r'\bcat\s+[^\n]*(\.env\b|credentials[\./]|\.netrc|\.pgpass|\.npmrc|\.pypirc)', re.IGNORECASE),
        "read_secrets_file",
        "attempt to directly read a secrets file",
    ),
    # prompt injection
    (
        re.compile(r'ignore\s+(previous|all|above|prior|any)\s+(previous\s+)?instructions?', re.IGNORECASE),
        "prompt_injection",
        "prompt injection pattern detected",
    ),
    (
        re.compile(r'disregard\s+(all|previous|prior)\s+instructions?', re.IGNORECASE),
        "prompt_injection_disregard",
        "prompt injection pattern detected",
    ),
    # destructive commands
    (
        re.compile(r'\brm\s+-[a-z]*r[a-z]*f[a-z]*\s+/', re.IGNORECASE),
        "destructive_rm_rf",
        "rm -rf targeting root — destructive command",
    ),
    (
        re.compile(r'\bmkfs\b|\bdd\s+if=/dev/zero', re.IGNORECASE),
        "destructive_disk",
        "disk destruction command detected",
    ),
    # remote code execution
    (
        re.compile(r'curl\s+[^\n]*\|\s*(bash|sh|python|ruby|perl)\b', re.IGNORECASE),
        "remote_code_exec",
        "curl pipe to shell — remote code execution risk",
    ),
    (
        re.compile(r'wget\s+[^\n]*-O\s*-\s*\|\s*(bash|sh)\b', re.IGNORECASE),
        "remote_code_exec_wget",
        "wget pipe to shell — remote code execution risk",
    ),
]


def scan_skill_content(content: str) -> tuple[bool, str]:
    """Scans the skill file content for security.

    Returns:
        (safe: bool, reason: str) — (True, "") if safe, (False, reason) if dangerous
"""
    for pattern, label, description in _PATTERNS:
        if pattern.search(content):
            return False, f"[{label}] {description}"
    return True, ""

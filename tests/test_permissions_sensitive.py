"""PermissionChecker — sensitive file deny pattern regression test.

Sensitive files such as `.env`, `*.pem`, `*.key`, `credentials*`, `secrets*`, `id_rsa` must be blocked from read/write/edit in any PermissionMode (including YOLO).

Red-Green:
1. Tests fail without is_sensitive_path() (Red)
2. Add pattern + helper + check_3step gate to permissions.py → pass (Green)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from hermit_agent.permissions import (
    PermissionBehavior,
    PermissionChecker,
    PermissionMode,
    is_sensitive_path,
)


@pytest.mark.parametrize(
    "path",
    [
        "/Users/x/project/.env",
        ".env",
        "/app/.env.local",
        "/tmp/.env.prod.local",
        "/etc/ssl/cert.pem",
        "server.key",
        "/home/u/.ssh/id_rsa",
        "/home/u/.ssh/id_ed25519",
        "credentials.json",
        "/secrets/credentials_prod.yaml",
        "secrets.yml",
        "/opt/secrets_prod.env",
    ],
)
def test_sensitive_paths_detected(path):
    assert is_sensitive_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        ".env.example",
        "/app/config.py",
        "api_key.py",
        "public.cer",
        "notes.md",
        "key_utils.go",
        ".envrc",
        "environment.md",
    ],
)
def test_non_sensitive_paths_pass(path):
    assert is_sensitive_path(path) is False


def test_read_sensitive_file_denied_in_yolo():
    checker = PermissionChecker(mode=PermissionMode.YOLO)
    result = checker.check_3step("read_file", {"path": "/x/.env"}, is_read_only=True)
    assert result.behavior == PermissionBehavior.DENY


def test_read_sensitive_file_denied_in_ask():
    checker = PermissionChecker(mode=PermissionMode.ASK)
    result = checker.check_3step("read_file", {"path": "/x/server.key"}, is_read_only=True)
    assert result.behavior == PermissionBehavior.DENY


def test_write_sensitive_file_denied():
    checker = PermissionChecker(mode=PermissionMode.ACCEPT_EDITS)
    result = checker.check_3step("write_file", {"path": "credentials.json", "content": "x"}, is_read_only=False)
    assert result.behavior == PermissionBehavior.DENY


def test_edit_sensitive_file_denied():
    checker = PermissionChecker(mode=PermissionMode.ACCEPT_EDITS)
    result = checker.check_3step("edit_file", {"path": ".env"}, is_read_only=False)
    assert result.behavior == PermissionBehavior.DENY


def test_non_sensitive_read_still_allowed_in_yolo():
    checker = PermissionChecker(mode=PermissionMode.YOLO)
    result = checker.check_3step("read_file", {"path": "/x/README.md"}, is_read_only=True)
    assert result.behavior == PermissionBehavior.ALLOW


def test_env_example_not_blocked():
    """The shared .env.example is not sensitive."""
    checker = PermissionChecker(mode=PermissionMode.YOLO)
    result = checker.check_3step("read_file", {"path": ".env.example"}, is_read_only=True)
    assert result.behavior == PermissionBehavior.ALLOW


def test_file_path_arg_name_also_checked():
    """The file_path argument name is also supported."""
    checker = PermissionChecker(mode=PermissionMode.YOLO)
    result = checker.check_3step("read_file", {"file_path": "/a/.env"}, is_read_only=True)
    assert result.behavior == PermissionBehavior.DENY

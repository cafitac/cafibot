"""G1 — session.jsonl structure validation."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermit_agent.session_logger import SessionLogger


def _read_jsonl(path: str) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def test_jsonl_file_is_created():
    with tempfile.TemporaryDirectory() as tmp:
        logger = SessionLogger(cwd=tmp)
        assert os.path.exists(logger.jsonl_path)
        assert logger.jsonl_path.endswith(".jsonl")


def test_user_record_format():
    with tempfile.TemporaryDirectory() as tmp:
        logger = SessionLogger(cwd=tmp)
        logger.log_user("hello world")
        records = _read_jsonl(logger.jsonl_path)
        user_records = [r for r in records if r.get("type") == "user"]
        assert len(user_records) == 1
        rec = user_records[0]
        assert rec["type"] == "user"
        assert "timestamp" in rec
        assert rec["content"] == "hello world"


def test_assistant_record_has_content_list():
    with tempfile.TemporaryDirectory() as tmp:
        logger = SessionLogger(cwd=tmp)
        logger.log_assistant_text("summary: done 1 thing")
        records = _read_jsonl(logger.jsonl_path)
        ar = [r for r in records if r.get("type") == "assistant"]
        assert len(ar) == 1
        rec = ar[0]
        assert isinstance(rec["content"], list)
        assert rec["content"][0]["type"] == "text"
        assert rec["content"][0]["text"] == "summary: done 1 thing"


def test_tool_use_and_tool_result_records():
    with tempfile.TemporaryDirectory() as tmp:
        logger = SessionLogger(cwd=tmp)
        logger.log_tool_use("use_1", "bash", {"command": "ls"})
        logger.log_tool_result("use_1", "file.txt\n", is_error=False)
        records = _read_jsonl(logger.jsonl_path)

        assistants = [r for r in records if r.get("type") == "assistant"]
        assert any(
            any(c.get("type") == "tool_use" and c.get("name") == "bash" for c in r["content"])
            for r in assistants
        )

        tr = [r for r in records if r.get("type") == "tool_result"]
        assert len(tr) == 1
        assert tr[0]["tool_use_id"] == "use_1"
        assert tr[0]["content"] == "file.txt\n"
        assert tr[0].get("is_error", False) is False


def test_attachment_record():
    with tempfile.TemporaryDirectory() as tmp:
        logger = SessionLogger(cwd=tmp)
        logger.log_attachment("compact", "~22k tokens compacted")
        records = _read_jsonl(logger.jsonl_path)
        att = [r for r in records if r.get("type") == "attachment"]
        assert len(att) == 1
        assert att[0]["kind"] == "compact"
        assert "22k" in att[0]["content"]


def test_permission_mode_record():
    with tempfile.TemporaryDirectory() as tmp:
        logger = SessionLogger(cwd=tmp)
        logger.log_permission_mode("yolo")
        records = _read_jsonl(logger.jsonl_path)
        pm = [r for r in records if r.get("type") == "permission-mode"]
        assert len(pm) == 1
        assert pm[0]["mode"] == "yolo"


def test_text_session_log_is_not_written():
    """session.log (text) is no longer generated — JSONL is the only log."""
    with tempfile.TemporaryDirectory() as tmp:
        logger = SessionLogger(cwd=tmp)
        logger.log_user("hi")
        # Structure simplification: remove .path attribute, no session.log file generation
        assert not hasattr(logger, "path") or not os.path.exists(getattr(logger, "path", ""))
        session_log = os.path.join(tmp, ".hermit", "session.log")
        assert not os.path.exists(session_log), "session.log should not be created"

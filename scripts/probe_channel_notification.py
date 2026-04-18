#!/usr/bin/env python3
"""Step 0 feasibility probe for hermit-channel merger.

Two responsibilities, both printed to stdout as JSON-RPC lines when
invoked as an MCP server over stdio:

1. Expose a `probe_emit` tool. When the MCP client calls it, this script
   sends a `notifications/claude/channel` notification via
   `await session._write_stream.send(SessionMessage(message=JSONRPCMessage(notif)))`.

2. Declare `experimental_capabilities = {"claude/channel": {}, "claude/channel/permission": {}}`
   at server initialization by lambda-wrapping `_mcp_server.create_initialization_options`.

The companion test (tests/test_mcp_notification_wire.py) drives this
script as a subprocess, sends a real initialize + tools/call sequence,
and asserts on both the initializeResult capabilities and the wire
format of the emitted notification.

This file is the executable artifact required by PRD US-000.
"""
from __future__ import annotations

import asyncio

from mcp.server.fastmcp import FastMCP
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage, JSONRPCNotification

SERVER_NAME = "hermit-channel"

PROBE_CONTENT = "<html>probe</html>"
PROBE_META = {
    "task_id": "t1",
    "type": "running",
    "step": "probe",
    "source": "hermit",
}


def _build() -> FastMCP:
    mcp_app = FastMCP(SERVER_NAME)

    original_create_init = mcp_app._mcp_server.create_initialization_options

    def create_init_with_channel_caps(**kw):
        kw.setdefault(
            "experimental_capabilities",
            {"claude/channel": {}, "claude/channel/permission": {}},
        )
        return original_create_init(**kw)

    mcp_app._mcp_server.create_initialization_options = create_init_with_channel_caps

    @mcp_app.tool()
    async def probe_emit() -> str:
        """Emit a notifications/claude/channel frame and return acknowledgement."""
        session = mcp_app.get_context().session
        notif = JSONRPCNotification(
            jsonrpc="2.0",
            method="notifications/claude/channel",
            params={"content": PROBE_CONTENT, "meta": PROBE_META},
        )
        message = JSONRPCMessage(notif)
        session_message = SessionMessage(message=message)
        await session._write_stream.send(session_message)
        return "emitted"

    return mcp_app


if __name__ == "__main__":
    asyncio.run(_build().run_stdio_async())

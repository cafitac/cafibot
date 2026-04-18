# Layer C Trace — HermitAgent ↔ Claude Code Boundary

**Date**: 2026-04-17
**Purpose**: Phase 2 (Layer C experiment) — Document how HermitAgent and Claude Code interact, and where the harness context can leak or become contaminated.

## Actual Relationship (Trace Results)

Initial hypothesis: "HermitAgent runs Claude Code as a subprocess" → **Incorrect**.

The actual structure is the **reverse**:

```
┌────────────────┐   MCP (stdio)   ┌─────────────────┐   HTTP   ┌────────────┐
│   Claude Code  │ ──────────────► │ hermit-channel │ ───────► │  HermitAgent   │
│   (host CLI)   │ ◄────────────── │   (Bun server)  │ ◄─────── │  (Python)  │
└────────────────┘                 └─────────────────┘          └────────────┘
         ▲                                   ▲                         │
         │                                   │                         │
         │      bash exec via proxy          │                         ▼
         └───────────────────────────────────┴──────────── host-exec-proxy
```

**Key Points:**
- Claude Code is the **host**, and hermit-channel is an **MCP server** from Claude Code's perspective (`hermit-channel/server.ts`).
- HermitAgent is a separate process, communicating bidirectionally with Claude Code via the channel.
- Route for HermitAgent to return questions to Claude Code: `notifications/claude/channel`.
- `host-exec-proxy.ts` — Used when Docker-internal HermitAgent executes host bash (arbitrary bash).

## No Direct `claude` CLI Invocation

Entire `hermit_agent/` grep results:
- `subprocess.Popen`, `subprocess.run` are used for **its own MCP server, pdftotext, pytest, git**.
- There is **no** code that directly spawns the `claude` or `cc` CLI.
- All "Claude Code reference" comments in `hermit_agent/tools/` are **for pattern reference** (reimplementation), not actual calls.

Conclusion: In terms of code paths, HermitAgent does not execute Claude Code.

## However, there are indirect paths

1. **Via `host-exec-proxy`**: If HermitAgent's `Bash` tool executes the `claude ...` command, a new Claude Code session starts on the host. This can occur in user workflows.
2. **Shared Filesystem**: HermitAgent also directly reads `~/.claude/skills/`, `~/.claude/commands/` (`hermit_agent/skills.py:70`, `mcp_server.py`). Thus, Claude Code's skills/commands are **also exposed to HermitAgent**.

## harness contamination points

| Path | Who loads it | Impact |
|---|---|---|
| `~/.claude/rules/*.md` | Claude Code only | Not passed to HermitAgent (isolated) |
| `~/.claude/skills/*` | **Both** | The same skill may behave differently on each side |
| `~/.claude/settings.json` hooks | Claude Code only | Not passed to HermitAgent |
| `CLAUDE.md` | Claude Code only | HermitAgent is separated to use `HERMIT.md` separately (Layer B) |
| `.claude/settings.json` permissions | Claude Code only | HermitAgent uses its own `permissions.py` |

## Recommendations

1. **Maintain isolation by default** — Place HermitAgent-specific context in `HERMIT.md` + `hermit_agent/hooks.py`, and use `CLAUDE.md` + `.claude/` exclusively for Claude Code.
2. **Make sharing explicit if necessary** — The current situation where `~/.claude/skills/` is loaded by both is "implicit sharing". To prevent future confusion:
- Separate skills read by HermitAgent into `~/.hermit/skills/`, or
- Explicitly mark shared skills (metadata like `audience: both`).
3. **host-exec-proxy security** — HermitAgent can execute arbitrary bash commands. Since the `claude` CLI can be executed on the host, permissions on the HermitAgent side must also be strict (`hermit_agent/permissions.py` already exists — subject to separate audit).

## Next steps (Hand-off to Phase 3)

- When designing the harness spec for HermitAgent itself, specify the **principle of role separation from CLAUDE.md/`.claude/`**.
- Need to decide whether the HermitAgent skill loader will continue sharing `~/.claude/skills/` or completely separate into `~/.hermit/skills/` (design topic).

# Server Hosting Mode Design

## Overview

Architecture for running HermitAgent + Ollama on Mac Studio with remote access for friends.
The infrastructure layer of the "I build and provide my own Claude Code" vision.

## Two Deployment Models

### Model A: API Provisioning (Remote Ollama)

```
Friend's Machine                    Mac Studio
┌───────────────────────┐       ┌──────────────────────┐
│  HermitAgent (local install)    │       │  Ollama API Server    │
│  AgentLoop            │──────→│  qwen3-coder-30b-64k │
│  tools (local exec)   │←──────│  :11434/v1           │
│  BashTool, ReadFile, etc      │       └──────────────────────┘
└───────────────────────┘
```

HermitAgent already supports `HERMIT_LLM_URL` + `HERMIT_MODEL` environment variables.

```bash
# Friend's configuration (.env or environment variables)
HERMIT_LLM_URL=https://hermit_agent.your-domain.com/v1
HERMIT_MODEL=qwen3-coder-30b-64k
HERMIT_API_KEY=key-issued-to-friend
```

**Pros:** Immediately implementable. No HermitAgent core changes needed.
**Cons:** Friends must install HermitAgent themselves.

---

### Model B: Harness Provisioning (Full CC Architecture Reproduction)

```
Friend's Machine                    Mac Studio
┌───────────────────────┐       ┌──────────────────────────┐
│  HermitAgent Client     │       │  HermitAgent AgentLoop       │
│  (Thin Client)        │       │  + Ollama (qwen3)        │
│                       │       │                          │
│  Tool Executor only   │←──────│  Sends tool_call          │
│  BashTool             │──────→│  Receives tool_result     │
│  ReadFile             │       │  → Next LLM inference     │
│  WriteFile            │       └──────────────────────────┘
│  RunTests, etc.       │
└───────────────────────┘
```

Inference on the server, tool execution on the client. Same principle as Claude Code.

---

## Model A Implementation Plan

### 1. Ollama API Authentication Layer

Ollama has no authentication by default. An authentication proxy is needed in front.

**Option 1: nginx reverse proxy + API key**
```nginx
location /v1/ {
    if ($http_authorization != "Bearer valid-key") {
        return 401;
    }
    proxy_pass http://localhost:11434/v1/;
}
```

**Option 2: Lightweight Python proxy (stdlib only)**
```python
# hermit_agent/server/api_proxy.py
# API key verification proxy based on http.server
# Forwards requests to Ollama
```

### 2. Concurrent Connection Limiting

With qwen3 (18GB) + Mac Studio 128GB:
- 1 model resident → max 1 concurrent inference (sequential processing)
- Queue management for waiting requests

```python
# Simple semaphore-based concurrency control
_inference_semaphore = threading.Semaphore(1)
```

### 3. Authentication Token Issuance Management

Simple file-based token management (`~/.hermit/server/tokens.json`):

```json
{
  "tokens": {
    "abc123": {"user": "friend-name", "created": "2026-04-14"},
    "def456": {"user": "another-friend", "created": "2026-04-14"}
  }
}
```

---

## Model B Implementation Plan

### Client-Server Protocol

A protocol where the server (Mac Studio) sends tool calls to the client (friend's machine) and receives results.

**WebSocket-based (Recommended):**

```
Client → Server: {type: "start", task: "/feature-develop 4086", cwd: "/path"}
Server → Client: {type: "tool_call", tool: "bash_tool", input: {"command": "git status"}}
Client → Server: {type: "tool_result", result: "On branch main..."}
Server → Client: {type: "tool_call", tool: "read_file", input: {"path": "..."}}
...
Server → Client: {type: "ask_user", question: "Is this change correct?"}
Client → User: Display question
User → Client: Answer
Client → Server: {type: "user_reply", message: "Yes, it is"}
Server → Client: {type: "done", result: "Complete"}
```

### Server-Side AgentLoop Modification

`RemoteToolExecutor` that delegates tool execution remotely:

```python
class RemoteToolExecutor:
    """Delegates tool execution to a WebSocket-connected client."""
    def execute(self, tool_name: str, input: dict) -> str:
        self._ws.send(json.dumps({"type": "tool_call", "tool": tool_name, "input": input}))
        result = self._ws.recv()  # Wait for client response
        return json.loads(result)["result"]
```

### Client (Thin Client)

Minimize installation size. Python stdlib only.

```bash
# Friend's installation
pip install hermit_agent-client  # Or download a single script

# Run
hermit_agent-client connect wss://hermit_agent.your-domain.com \
  --token key-issued-to-friend \
  --task "/feature-develop 4086" \
  --cwd /path/to/repo
```

---

## Security Considerations

| Threat | Response |
|--------|----------|
| Unauthorized API access | API key authentication |
| Malicious tool execution | Controlled via client-side PermissionMode |
| Excessive LLM usage | Token/request rate limiting |
| Network eavesdropping | HTTPS/WSS required |
| Direct LLM server exposure | ollama `127.0.0.1` binding + authentication proxy front-end |
| Filesystem escape | `_is_safe_path(cwd)` validation, Docker volume mount restrictions |

> For isolation architecture, audit logging, and anomaly detection strategies, see [security.md](security.md).

---

## HermitAgent ↔ Claude Code File Reference Separation Policy

HermitAgent command files currently reference `~/.claude/` paths directly:
- `~/.claude/rules/code-rules.md` — Code review criteria
- `~/.claude/skills/code-standards/` — Standard patterns
- `~/.claude/skills/learned-feedback/` — Learned feedback
- `~/.claude/templates/` — PR description, worktree-setup, etc.
- `~/.claude/scripts/` — code-review.py, code-test.sh, etc.

**Current Policy (2026-04-16): Keep References**

Since CC and HermitAgent run together on the same machine, `~/.claude/` always exists.
When CC updates rules/skills, HermitAgent automatically uses the latest version.
Copying would create a synchronization burden — maintaining references is more practical at this point.

**Separation Trigger: External Deployment Beyond Mac Studio**

In environments where HermitAgent runs standalone without CC (e.g., Mac Studio server):
1. Set up `~/.hermit/rules/`, `~/.hermit/skills/`, `~/.hermit/templates/` directories
2. Replace all `~/.claude/` references in HermitAgent command files with `~/.hermit/`
3. Copy `~/.claude/scripts/*.py`, `~/.claude/scripts/*.sh` to `~/.hermit/scripts/`

---

## Implementation Priority

**Phase 1 (Immediate):** Model A
- Ollama API authentication proxy
- Token issuance CLI
- 1 concurrent connection limit

**Phase 2 (After Stabilization):** Model B
- WebSocket protocol design
- RemoteToolExecutor implementation
- Thin client packaging

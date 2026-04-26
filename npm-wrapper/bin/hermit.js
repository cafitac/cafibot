#!/usr/bin/env node
import { spawnHermit, readWrapperVersion } from "../lib/runtime.js";
import { buildUpdateHintLines, checkForUpdates, runSelfUpdate } from "../lib/updates.js";

try {
  const rawArgs = process.argv.slice(2);
  const args = rawArgs.filter((arg) => arg !== "--no-update-check");
  const command = args[0] ?? "";
  const wrapperVersion = await readWrapperVersion();

  if (command === "version" || rawArgs.includes("--version") || rawArgs.includes("-v")) {
    console.log(wrapperVersion);
    process.exit(0);
  }

  if (command === "help" || rawArgs.includes("--help") || rawArgs.includes("-h")) {
    console.log(`hermit v${wrapperVersion} — Local LLM Coding Agent

Usage:
  hermit                        Interactive TUI (default)
  hermit "<message>"            Single message (CLI mode)
  hermit <command> [options]

Commands:
  install                       Guided setup / install flow
  setup-claude                  Prepare Hermit's Claude Code integration
  setup-codex                   Prepare Hermit's Codex integration
  doctor                        Diagnose and repair common setup issues
  status                        Show agent / gateway status
  config local-backend          Detect or set local LLM backend (mlx, llama.cpp, ollama)
  update, self-update           Update hermit to the latest version
  version                       Show version number
  help                          Show this help message

Agent options (single-message mode):
  --model <name>                Model to use
  --base-url <url>              API base URL (default: http://localhost:8765/v1)
  --api-key <key>               Bearer token for the gateway
  --yolo                        Skip all permission checks
  --ask                         Ask permission for every tool call
  --accept-edits                Auto-allow reads+edits, ask for bash
  --dont-ask                    Allow everything silently with logging
  --plan                        Read-only mode (block all writes)
  --channel <cli|none>          Channel interface
  --no-stream                   Disable streaming output
  --max-turns <n>               Max agent turns (default: 50)
  --max-context <n>             Max context tokens (default: 32000)
  --fallback-model <name>       Fallback model after repeated failures

Startup flags:
  --no-update-check             Skip update check on startup
  --version, -v                 Show version number
  --help, -h                    Show this help message`);
    process.exit(0);
  }

  if (command === "self-update" || command === "update") {
    const result = await runSelfUpdate();
    if (!result.ok) {
      console.error(`[HERMIT] ${result.message}`);
      process.exit(1);
    }
    console.log(`[HERMIT] ${result.message}`);
    process.exit(0);
  }

  if (process.stdout.isTTY && process.stderr.isTTY && !rawArgs.includes("--no-update-check")) {
    try {
      const availability = await checkForUpdates();
      if (availability) {
        for (const line of buildUpdateHintLines(availability)) {
          console.error(line);
        }
      }
    } catch {
      // Update checks are advisory only.
    }
  }

  await spawnHermit({ args, wrapperVersion });
} catch (error) {
  console.error(`[hermit npm wrapper] ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}

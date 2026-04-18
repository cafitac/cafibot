#!/usr/bin/env bash
# HermitAgent one-shot installer.
#
# Creates a project-local venv, bootstraps uv inside it, installs the
# Python package via uv, writes a default ~/.hermit/settings.json if
# missing, and (optionally) pulls a local ollama coding model.
# Idempotent — safe to re-run.
#
# Usage:
#   ./install.sh                 # interactive
#   ./install.sh --no-ollama     # skip the ollama prompt
#   ./install.sh --skip-venv     # reuse an existing .venv

set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
SETTINGS_DIR="$HOME/.hermit"
SETTINGS_FILE="$SETTINGS_DIR/settings.json"

SKIP_OLLAMA=0
SKIP_VENV=0
for arg in "$@"; do
  case "$arg" in
    --no-ollama) SKIP_OLLAMA=1 ;;
    --skip-venv) SKIP_VENV=1 ;;
    -h|--help)
      sed -n '2,13p' "$0"
      exit 0
      ;;
  esac
done

say()  { printf "\033[1;36m▸\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!\033[0m %s\n" "$*" >&2; }

# 1. Python version check
if ! command -v python3 >/dev/null; then
  warn "python3 not found on PATH. Install Python 3.11+ first."
  exit 1
fi
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
  warn "Python 3.11+ required (found $PY_MAJOR.$PY_MINOR)."
  exit 1
fi

# 2. venv
if [ "$SKIP_VENV" -eq 0 ]; then
  if [ -d "$VENV_DIR" ]; then
    say "Reusing existing venv at $VENV_DIR"
  else
    say "Creating venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi
fi

VENV_PY="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"
VENV_UV="$VENV_DIR/bin/uv"

# 3. bootstrap uv inside the venv — single pip invocation, everything
#    else runs through uv (much faster resolver + installer).
if [ ! -x "$VENV_UV" ]; then
  say "Bootstrapping uv inside the venv"
  "$VENV_PIP" install --quiet --upgrade pip
  "$VENV_PIP" install --quiet uv
fi

# 4. deps — all via uv
say "Installing project (uv pip install -e .)"
"$VENV_UV" pip install --python "$VENV_PY" -e ".[test]" --quiet

# 5. settings.json scaffold
mkdir -p "$SETTINGS_DIR"
if [ -f "$SETTINGS_FILE" ]; then
  say "Found existing settings at $SETTINGS_FILE — leaving it alone"
else
  say "Writing default settings to $SETTINGS_FILE"
  cat > "$SETTINGS_FILE" <<'EOF'
{
  "gateway_url": "http://localhost:8765",
  "gateway_api_key": "CHANGE_ME_AFTER_FIRST_RUN",
  "model": "glm-5.1",
  "response_language": "auto",
  "compact_instructions": ""
}
EOF
  warn "Edit $SETTINGS_FILE — set gateway_api_key (see docs/cc-setup.md) and pick a model."
fi

# 6. optional: ollama model pull. Keep this non-fatal — users with a
#    working z.ai / cloud-only setup don't need a local model, and a
#    misconfigured OLLAMA_MODELS (pointing at unmounted external
#    storage, etc.) should not abort the rest of the install.
if [ "$SKIP_OLLAMA" -eq 0 ] && command -v ollama >/dev/null; then
  printf "\033[1;36m▸\033[0m Pull a local coding model via ollama? [y/N] "
  read -r reply || reply="n"
  if [[ "$reply" =~ ^[Yy]$ ]]; then
    say "Pulling qwen3-coder:30b (this can take a while — ~18GB)"
    if ! ollama pull qwen3-coder:30b; then
      warn "ollama pull failed. Check OLLAMA_MODELS and the path it points to."
      warn "Hermit runs fine with a cloud executor alone — leave model=glm-5.1 (or similar) in ~/.hermit/settings.json to skip local models."
    fi
  fi
fi

# 7. symlink the -hermit slash commands into the user's Claude Code
#    config so `/feature-develop-hermit` etc. resolve. Symlinks (not
#    copies) mean `git pull` in this repo is picked up automatically.
USER_CC_COMMANDS="$HOME/.claude/commands"
mkdir -p "$USER_CC_COMMANDS"
for f in "$PROJECT_DIR"/.claude/commands/*-hermit.md; do
  [ -e "$f" ] || continue
  name="$(basename "$f")"
  target="$USER_CC_COMMANDS/$name"
  if [ -L "$target" ] || [ ! -e "$target" ]; then
    ln -sf "$f" "$target"
    say "Linked $name → $USER_CC_COMMANDS/"
  else
    warn "Skipped $name — a regular file already exists at $target (not overwritten)."
  fi
done

# 8. sanity check
say "Sanity check — importing hermit_agent"
"$VENV_PY" -c 'import hermit_agent; print("  version:", hermit_agent.__version__ if hasattr(hermit_agent, "__version__") else "dev")'

say "Done. Next steps:"
echo "  1. Start the gateway:  ./gateway.sh --daemon"
echo "  2. Register MCP server in Claude Code — see docs/cc-setup.md"
echo "  3. In Claude Code, try one of the bundled reference skills"
echo "     (e.g. /feature-develop-hermit <task>), or read"
echo "     docs/hermit-variants.md and fork your own."

"""Plugin system — based on claw-code's PluginManager/PluginRegistry pattern.

Plugin directory structure:
  ~/.hermit/plugins/
    my-plugin/
      plugin.json          ← manifest
      hooks/
        pre.sh             ← PreToolUse hook
        post.sh            ← PostToolUse hook
      tools/
        my_tool.py         ← custom tool (optional)

plugin.json example:
  {
    "name": "my-plugin",
    "version": "1.0.0",
    "description": "My custom plugin",
    "hooks": {
      "PreToolUse": ["./hooks/pre.sh"],
      "PostToolUse": ["./hooks/post.sh"]
    },
    "tools": ["./tools/my_tool.py"]
  }
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


PLUGINS_DIR = os.path.expanduser("~/.hermit/plugins")
PLUGIN_MANIFEST = "plugin.json"


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    hooks_pre: list[str] = field(default_factory=list)  # PreToolUse hook commands
    hooks_post: list[str] = field(default_factory=list)  # PostToolUse hook commands
    tool_scripts: list[str] = field(default_factory=list)
    enabled: bool = True
    path: str = ""


@dataclass
class PluginTool:
    """Tool provided by a plugin."""
    name: str
    description: str
    input_schema: dict
    command: str  # script path to execute
    plugin_name: str


class PluginManager:
    """Plugin install/enable/disable management."""

    def __init__(self):
        os.makedirs(PLUGINS_DIR, exist_ok=True)
        self.plugins: dict[str, PluginManifest] = {}
        self._load_installed()

    def _load_installed(self):
        """Load installed plugins."""
        for entry in Path(PLUGINS_DIR).iterdir():
            if not entry.is_dir():
                continue
            manifest_path = entry / PLUGIN_MANIFEST
            if not manifest_path.exists():
                continue
            try:
                manifest = _parse_manifest(manifest_path, str(entry))
                self.plugins[manifest.name] = manifest
            except Exception:
                continue

    def install(self, source_path: str) -> str:
        """Install a plugin from a local path."""
        source = Path(source_path)
        manifest_path = source / PLUGIN_MANIFEST
        if not manifest_path.exists():
            raise ValueError(f"No {PLUGIN_MANIFEST} found in {source_path}")

        manifest = _parse_manifest(manifest_path, source_path)
        dest = Path(PLUGINS_DIR) / manifest.name

        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)

        # Grant execute permission to hook scripts
        for hook_dir in (dest / "hooks",):
            if hook_dir.exists():
                for f in hook_dir.iterdir():
                    if f.is_file():
                        f.chmod(0o755)

        manifest.path = str(dest)
        self.plugins[manifest.name] = manifest
        return f"Installed: {manifest.name} v{manifest.version}"

    def uninstall(self, name: str) -> str:
        dest = Path(PLUGINS_DIR) / name
        if dest.exists():
            shutil.rmtree(dest)
        self.plugins.pop(name, None)
        return f"Uninstalled: {name}"

    def enable(self, name: str) -> bool:
        if name in self.plugins:
            self.plugins[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        if name in self.plugins:
            self.plugins[name].enabled = False
            return True
        return False

    def list_plugins(self) -> list[PluginManifest]:
        return list(self.plugins.values())

    def get_enabled(self) -> list[PluginManifest]:
        return [p for p in self.plugins.values() if p.enabled]


class PluginRegistry:
    """Collect hooks and tools from active plugins."""

    def __init__(self, manager: PluginManager | None = None):
        self.manager = manager or PluginManager()
        self._pre_hooks: list[tuple[str, str]] = []  # (plugin_name, command)
        self._post_hooks: list[tuple[str, str]] = []
        self._tools: list[PluginTool] = []
        self._collect()

    def _collect(self):
        for plugin in self.manager.get_enabled():
            plugin_dir = Path(plugin.path) if plugin.path else Path(PLUGINS_DIR) / plugin.name

            # Collect hooks
            for cmd in plugin.hooks_pre:
                resolved = str(plugin_dir / cmd) if not os.path.isabs(cmd) else cmd
                self._pre_hooks.append((plugin.name, resolved))

            for cmd in plugin.hooks_post:
                resolved = str(plugin_dir / cmd) if not os.path.isabs(cmd) else cmd
                self._post_hooks.append((plugin.name, resolved))

            for script_path in plugin.tool_scripts:
                resolved = str(plugin_dir / script_path) if not os.path.isabs(script_path) else script_path
                tool = self._load_tool_script(resolved, plugin.name)
                if tool:
                    self._tools.append(tool)

    def _load_tool_script(self, path: str, plugin_name: str) -> PluginTool | None:
        """Load a Python tool script. Script must define name, description, input_schema, execute."""
        import importlib.util
        try:
            spec = importlib.util.spec_from_file_location(f"plugin_tool_{plugin_name}", path)
            if not spec or not spec.loader:
                return None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return PluginTool(
                name=getattr(mod, 'name', ''),
                description=getattr(mod, 'description', ''),
                input_schema=getattr(mod, 'input_schema', {}),
                command=path,
                plugin_name=plugin_name,
            )
        except Exception:
            return None

    @property
    def tools(self) -> list[PluginTool]:
        return self._tools

    @property
    def pre_tool_hooks(self) -> list[tuple[str, str]]:
        return self._pre_hooks

    @property
    def post_tool_hooks(self) -> list[tuple[str, str]]:
        return self._post_hooks

    def run_pre_hooks(self, tool_name: str, tool_input: str) -> tuple[bool, list[str]]:
        """Execute PreToolUse hooks. Returns (denied, messages)."""
        return self._run_hooks(self._pre_hooks, "PreToolUse", tool_name, tool_input)

    def run_post_hooks(self, tool_name: str, tool_input: str, tool_output: str, is_error: bool = False) -> list[str]:
        """Execute PostToolUse hooks."""
        _, messages = self._run_hooks(
            self._post_hooks, "PostToolUse", tool_name, tool_input,
            tool_output=tool_output, is_error=is_error,
        )
        return messages

    def _run_hooks(
        self,
        hooks: list[tuple[str, str]],
        event: str,
        tool_name: str,
        tool_input: str,
        tool_output: str | None = None,
        is_error: bool = False,
    ) -> tuple[bool, list[str]]:
        messages = []

        for plugin_name, command in hooks:
            env = {
                **os.environ,
                "HOOK_EVENT": event,
                "HOOK_TOOL_NAME": tool_name,
                "HOOK_TOOL_INPUT": tool_input,
                "HOOK_TOOL_IS_ERROR": "1" if is_error else "0",
            }
            if tool_output:
                env["HOOK_TOOL_OUTPUT"] = tool_output[:5000]

            payload = json.dumps({
                "hook_event_name": event,
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_output": tool_output,
                "tool_result_is_error": is_error,
            })

            try:
                result = subprocess.run(
                    ["sh", "-c", command] if not os.path.isabs(command) else [command],
                    input=payload, capture_output=True, text=True,
                    timeout=10, env=env,
                )
                stdout = result.stdout.strip()

                if result.returncode == 0:
                    if stdout:
                        messages.append(stdout)
                elif result.returncode == 2:
                    # exit 2 = deny (claw-code pattern)
                    messages.append(stdout or f"{event} hook from {plugin_name} denied {tool_name}")
                    return True, messages
                else:
                    messages.append(f"Hook warning ({plugin_name}): exit {result.returncode}")
            except Exception as e:
                messages.append(f"Hook error ({plugin_name}): {e}")

        return False, messages


def _parse_manifest(path: Path, plugin_dir: str) -> PluginManifest:
    with open(path) as f:
        data = json.load(f)

    hooks = data.get("hooks", {})

    return PluginManifest(
        name=data["name"],
        version=data.get("version", "0.0.0"),
        description=data.get("description", ""),
        hooks_pre=hooks.get("PreToolUse", []),
        hooks_post=hooks.get("PostToolUse", []),
        tool_scripts=data.get("tools", []),
        path=plugin_dir,
    )

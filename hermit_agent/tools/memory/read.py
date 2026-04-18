"""Memory read tool (MemoryReadTool)."""

from __future__ import annotations

from ..base import Tool, ToolResult


class MemoryReadTool(Tool):
    """Memory read tool."""
    name = "memory_read"
    description = "Read saved memories. Returns the memory index or a specific memory by name."
    is_read_only = True
    is_concurrent_safe = True

    def __init__(self):
        from ...memory import MemorySystem
        self.memory = MemorySystem()

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Memory name to read. Omit to list all memories.",
                },
            },
            "required": [],
        }

    def execute(self, input: dict) -> ToolResult:
        name = input.get("name")
        if name:
            entry = self.memory.load(name)
            if entry:
                return ToolResult(content=f"# {entry.name} ({entry.mem_type})\n\n{entry.content}")
            return ToolResult(content=f"Memory not found: {name}", is_error=True)
        return ToolResult(content=self.memory.get_index())


__all__ = ['MemoryReadTool']

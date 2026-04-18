"""Memory write tool (MemoryWriteTool)."""

from __future__ import annotations

from ..base import Tool, ToolResult


class MemoryWriteTool(Tool):
    name = "memory_write"
    description = "Save information to persistent memory for future conversations. Use for user preferences, project context, or important decisions."

    def __init__(self):
        from ...memory import MemorySystem
        self.memory = MemorySystem()

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Short name for this memory (e.g. 'project_stack', 'user_preference')",
                },
                "content": {
                    "type": "string",
                    "description": "The information to remember",
                },
                "type": {
                    "type": "string",
                    "enum": ["user", "project", "feedback", "reference"],
                    "description": "Memory type (default: project)",
                },
                "description": {
                    "type": "string",
                    "description": "One-line description of this memory",
                },
            },
            "required": ["name", "content"],
        }

    def execute(self, input: dict) -> ToolResult:
        name = input["name"]
        content = input["content"]
        mem_type = input.get("type", "project")
        description = input.get("description", name)

        filepath = self.memory.save(name, content, mem_type, description)
        return ToolResult(content=f"Memory saved: {name} → {filepath}")


__all__ = ['MemoryWriteTool']

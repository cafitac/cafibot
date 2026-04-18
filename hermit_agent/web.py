"""Web search and page fetch tools — backward-compatible re-export.

The actual implementation has been moved to the hermit_agent/tools/web/ package.
"""

from .tools.web import (  # noqa: F401
    DeepSearchTool,
    GitHubSearchTool,
    StackOverflowSearchTool,
    WebFetchTool,
    WebSearchTool,
)

__all__ = [
    "WebSearchTool",
    "WebFetchTool",
    "DeepSearchTool",
    "StackOverflowSearchTool",
    "GitHubSearchTool",
]

"""DeepSearchTool — multi-source cross-verified search."""

from __future__ import annotations

from ..base import Tool, ToolResult
from .fetch import WebFetchTool
from .search import WebSearchTool


class DeepSearchTool(Tool):
    name = "deep_search"
    description = (
        "Deep search: search the web, fetch top results, and cross-verify information "
        "from multiple sources to minimize hallucination."
    )
    is_read_only = True

    def __init__(self, web_search: WebSearchTool, web_fetch: WebFetchTool):
        self._search = web_search
        self._fetch = web_fetch

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query to investigate deeply"},
                "num_sources": {"type": "integer", "description": "Number of sources to fetch (default: 3)", "default": 3},
            },
            "required": ["query"],
        }

    def execute(self, input: dict) -> ToolResult:
        query = input["query"]
        num_sources = input.get("num_sources", 3)

        search_result = self._search.execute({"query": query, "max_results": num_sources + 2})
        if search_result.is_error:
            return search_result

        urls: list[str] = []
        for line in search_result.content.splitlines():
            stripped = line.strip()
            if stripped.startswith("URL: "):
                url = stripped[5:].strip()
                if url:
                    urls.append(url)
                if len(urls) >= num_sources:
                    break

        if not urls:
            return ToolResult(content=f"No URLs found in search results for: {query}", is_error=True)

        sections: list[str] = [f"Deep search results for: {query}\n"]
        sections.append(search_result.content)
        sections.append("\n" + "=" * 60 + "\n")

        fetched_count = 0
        for url in urls:
            fetch_result = self._fetch.execute({"url": url, "prompt": query})
            if not fetch_result.is_error:
                sections.append(f"--- Source: {url} ---")
                sections.append(fetch_result.content[:5000])
                sections.append("")
                fetched_count += 1

        if fetched_count == 0:
            return ToolResult(content=f"Could not fetch any sources for: {query}", is_error=True)

        sections.append("=" * 60)
        sections.append(
            "\nInstruction: Cross-verify the above sources. "
            "Note agreements and disagreements. Cite sources for claims."
        )

        return ToolResult(content="\n".join(sections))


__all__ = ["DeepSearchTool"]

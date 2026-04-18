"""StackOverflowSearchTool — Stack Overflow programming Q&A search."""

from __future__ import annotations

import urllib.parse

import requests

from ..base import Tool, ToolResult


class StackOverflowSearchTool(Tool):
    """Stack Overflow search — specialized for programming Q&A."""

    name = "stackoverflow_search"
    description = "Search Stack Overflow for programming Q&A. Best for error messages, how-to questions, and coding patterns."
    is_read_only = True
    is_concurrent_safe = True

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Programming question or error message to search"},
                "tags": {"type": "string", "description": "Comma-separated tags (e.g. 'python,django')"},
            },
            "required": ["query"],
        }

    def execute(self, input: dict) -> ToolResult:
        import gzip
        import json
        import re

        query = input["query"]
        tags = input.get("tags", "")

        params = {
            "order": "desc",
            "sort": "relevance",
            "intitle": query[:150],
            "site": "stackoverflow",
            "pagesize": "5",
        }
        if tags:
            params["tagged"] = tags.replace(" ", "").replace(",", ";")

        url = "https://api.stackexchange.com/2.3/search?" + urllib.parse.urlencode(params)

        try:
            resp = requests.get(url, headers={"User-Agent": "HermitAgent/0.1", "Accept-Encoding": "identity"}, timeout=15)
            resp.raise_for_status()
            raw = resp.content
            try:
                data = json.loads(gzip.decompress(raw))
            except Exception:
                data = json.loads(raw)

            items = data.get("items", [])
            if not items:
                return ToolResult(content=f"No Stack Overflow results for: {query}")

            lines = [f"Stack Overflow results for: {query}\n"]
            for i, item in enumerate(items[:5], 1):
                title = item.get("title", "")
                link = item.get("link", "")
                score = item.get("score", 0)
                answered = item.get("is_answered", False)
                answer_count = item.get("answer_count", 0)
                tags_list = item.get("tags", [])

                lines.append(f"{i}. [{score}↑] {title}")
                lines.append(f"   URL: {link}")
                lines.append(f"   Tags: {', '.join(tags_list[:5])} | Answers: {answer_count} | Answered: {answered}")

                body = item.get("body", "")
                if body:
                    text = re.sub(r'<[^>]+>', '', body)[:300]
                    lines.append(f"   {text.strip()}")
                lines.append("")

            quota = data.get("quota_remaining", "?")
            lines.append(f"(API quota remaining: {quota})")
            return ToolResult(content="\n".join(lines))

        except Exception as e:
            return ToolResult(content=f"Stack Overflow search error: {e}", is_error=True)


__all__ = ["StackOverflowSearchTool"]

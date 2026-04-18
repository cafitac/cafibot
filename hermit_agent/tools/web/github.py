"""GitHubSearchTool — GitHub code/repository/issue search."""

from __future__ import annotations

import subprocess
import urllib.parse

import requests

from ..base import Tool, ToolResult


class GitHubSearchTool(Tool):
    """GitHub search — code, repositories, and issues."""

    name = "github_search"
    description = "Search GitHub for code, repositories, and issues. Use for finding implementations, libraries, and code examples."
    is_read_only = True
    is_concurrent_safe = True

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "search_type": {
                    "type": "string",
                    "enum": ["repositories", "code", "issues"],
                    "description": "Type of search (default: repositories)",
                },
                "language": {"type": "string", "description": "Filter by language (e.g. 'python', 'typescript')"},
            },
            "required": ["query"],
        }

    def execute(self, input: dict) -> ToolResult:
        import json

        query = input["query"]
        search_type = input.get("search_type", "repositories")
        language = input.get("language", "")

        # Use gh CLI (authenticated)
        try:
            if search_type == "repositories":
                cmd = ["gh", "search", "repos", query, "--limit", "5", "--json", "name,owner,description,stargazersCount,url,language"]
                if language:
                    cmd.extend(["--language", language])
            elif search_type == "code":
                cmd = ["gh", "search", "code", query, "--limit", "5", "--json", "repository,path,textMatches"]
                if language:
                    cmd.extend(["--language", language])
            elif search_type == "issues":
                cmd = ["gh", "search", "issues", query, "--limit", "5", "--json", "title,url,state,repository,createdAt"]
            else:
                cmd = ["gh", "search", "repos", query, "--limit", "5", "--json", "name,owner,description,stargazersCount,url"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and result.stdout.strip():
                items = json.loads(result.stdout)
                return ToolResult(content=self._format_results(items, search_type, query))
        except (FileNotFoundError, Exception):
            pass

        # Fallback: GitHub REST API
        try:
            q = query + (f" language:{language}" if language else "")
            api_type = {"repositories": "repositories", "code": "code", "issues": "issues"}.get(search_type, "repositories")
            url = f"https://api.github.com/search/{api_type}?q={urllib.parse.quote(q)}&per_page=5&sort=stars"

            resp = requests.get(url, headers={"User-Agent": "HermitAgent/0.1", "Accept": "application/vnd.github.v3+json"}, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("items", [])
            if not items:
                return ToolResult(content=f"No GitHub results for: {query}")

            lines = [f"GitHub {search_type} for: {query}\n"]
            for i, item in enumerate(items[:5], 1):
                if search_type == "repositories":
                    lines.append(f"{i}. ⭐{item.get('stargazers_count', 0)} {item.get('full_name', '')} [{item.get('language', '')}]")
                    lines.append(f"   {(item.get('description', '') or '')[:100]}")
                    lines.append(f"   {item.get('html_url', '')}")
                elif search_type == "issues":
                    lines.append(f"{i}. [{item.get('state', '')}] {item.get('title', '')}")
                    lines.append(f"   {item.get('html_url', '')}")
                lines.append("")
            return ToolResult(content="\n".join(lines))

        except Exception as e:
            return ToolResult(content=f"GitHub search error: {e}", is_error=True)

    def _format_results(self, items: list, search_type: str, query: str) -> str:
        lines = [f"GitHub {search_type} for: {query}\n"]
        for i, item in enumerate(items[:5], 1):
            if search_type == "repositories":
                owner = item.get("owner", {}).get("login", "") if isinstance(item.get("owner"), dict) else str(item.get("owner", ""))
                lines.append(f"{i}. ⭐{item.get('stargazersCount', 0)} {owner}/{item.get('name', '')} [{item.get('language', '')}]")
                lines.append(f"   {(item.get('description', '') or '')[:100]}")
                lines.append(f"   {item.get('url', '')}")
            elif search_type == "code":
                repo = item.get("repository", {})
                repo_name = repo.get("nameWithOwner", "") if isinstance(repo, dict) else str(repo)
                lines.append(f"{i}. {repo_name}: {item.get('path', '')}")
            elif search_type == "issues":
                lines.append(f"{i}. [{item.get('state', '')}] {item.get('title', '')}")
                lines.append(f"   {item.get('url', '')}")
            lines.append("")
        return "\n".join(lines)


__all__ = ["GitHubSearchTool"]

"""WebFetchTool — URL content extraction."""

from __future__ import annotations

import urllib.parse

import requests

from ..base import Tool, ToolResult


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetch content from a URL and extract information. Takes a URL and a prompt describing what to extract."
    is_read_only = True
    is_concurrent_safe = True

    CONTENT_LIMIT = 15000

    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "prompt": {"type": "string", "description": "What to extract or look for in the fetched content"},
            },
            "required": ["url", "prompt"],
        }

    def validate(self, input: dict) -> str | None:
        url = input.get("url", "")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return f"Invalid URL: must start with http:// or https://, got: {url!r}"
        if not parsed.netloc:
            return f"Invalid URL: missing host in {url!r}"
        return None

    def execute(self, input: dict) -> ToolResult:
        error = self.validate(input)
        if error:
            return ToolResult(content=error, is_error=True)

        url = input["url"]
        prompt = input["prompt"]

        try:
            import html2text

            resp = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) HermitAgent/0.1",
                    "Accept": "text/html,application/xhtml+xml,*/*",
                },
                timeout=30,
            )
            resp.raise_for_status()
            html_content = resp.content.decode("utf-8", errors="replace")

            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.body_width = 0
            markdown = h.handle(html_content)

            truncated = markdown[:self.CONTENT_LIMIT]
            if len(markdown) > self.CONTENT_LIMIT:
                truncated += f"\n\n... (truncated, {len(markdown) - self.CONTENT_LIMIT} chars omitted)"

            content = f"Instruction: {prompt}\n\nContent from {url}:\n\n{truncated}"
            return ToolResult(content=content)

        except ImportError:
            return ToolResult(content="html2text library not installed. Run: pip install html2text", is_error=True)
        except requests.HTTPError as e:
            return ToolResult(content=f"HTTP error {e.response.status_code} fetching {url}: {e}", is_error=True)
        except requests.RequestException as e:
            return ToolResult(content=f"URL error fetching {url}: {e}", is_error=True)
        except TimeoutError:
            return ToolResult(content=f"Timeout fetching {url} (30s)", is_error=True)
        except Exception as e:
            return ToolResult(content=f"Error fetching {url}: {e}", is_error=True)


__all__ = ["WebFetchTool"]

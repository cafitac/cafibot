"""Shared singletons — standalone module to prevent circular imports."""
import os

from .sse import SSEManager

sse_manager = SSEManager()
MAX_WORKERS = int(os.environ.get("GATEWAY_MAX_WORKERS", "20"))

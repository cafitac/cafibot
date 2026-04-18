"""pytest config — auto-exclude Ollama-dependent integration tests."""

collect_ignore = [
    "tests/test_tool_calling.py",  # Requires Ollama server + model installed
]

"""Deepinit — AI-readable codebase documentation via hierarchical AGENTS.md auto-generation."""

import os


def generate_agents_md(cwd: str, llm) -> list[str]:
    """Create AGENTS.md in each main directory. Return the list of created file paths."""
    created = []
    # Find directories with source files
    for root, dirs, files in os.walk(cwd):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', '.git', 'venv', '.venv')]
        source_files = [f for f in files if f.endswith(('.py', '.ts', '.tsx', '.js', '.jsx', '.go', '.rs', '.java'))]
        if not source_files or len(source_files) < 2:
            continue

        agents_path = os.path.join(root, 'AGENTS.md')
        if os.path.exists(agents_path):
            continue

        # Generate doc using LLM
        file_list = '\n'.join(f'- {f}' for f in source_files[:20])
        # Read first 30 lines of each file for context
        snippets = []
        for f in source_files[:5]:
            try:
                with open(os.path.join(root, f)) as fh:
                    snippet = ''.join(fh.readlines()[:30])
                snippets.append(f"### {f}\n```\n{snippet}\n```")
            except Exception:
                pass

        prompt = f"Generate a concise AGENTS.md for this directory.\n\nPath: {root}\nFiles:\n{file_list}\n\nCode samples:\n{''.join(snippets[:3])}\n\nFormat:\n# {os.path.basename(root)}\n\n## Purpose\n...\n\n## Key Files\n...\n\n## Conventions\n..."

        response = llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="Generate concise directory documentation. Markdown format.",
        )
        if response.content:
            with open(agents_path, 'w') as f:
                f.write(response.content)
            created.append(agents_path)

    return created

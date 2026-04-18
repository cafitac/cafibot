"""CLIChannel — terminal stdin/stdout based channel."""
from __future__ import annotations

import sys

from .base import ChannelInterface


class CLIChannel(ChannelInterface):
    """Channel for conversing with HermitAgent directly from the terminal.

    - Progress: printed to stdout
    - Questions: printed to stdout, answers collected from stdin
    - Completion results: printed to stdout

    Usage example:
        channel = CLIChannel()
        tools = create_default_tools(
            cwd="/path/to/repo",
            question_queue=channel.question_queue,
            reply_queue=channel.reply_queue,
        )
        agent = AgentLoop(
            llm=llm,
            tools=tools,
            cwd="/path/to/repo",
            permission_mode=PermissionMode.YOLO,
            on_tool_result=channel.make_progress_hook(),
        )
        channel.start()
        try:
            result = agent.run("/feature-develop 4086")
            channel.send(result)
        finally:
            channel.stop()
    """

    def send(self, message: str) -> None:
        """Print progress/results to stdout."""
        print(f"\n[HermitAgent] {message}", flush=True)

    def _answer_loop(self) -> None:
        """Watch question_queue; when a question arrives, print it and collect an answer from stdin."""
        while not self._stop_event.is_set():
            try:
                qdata = self.question_queue.get(timeout=0.5)
            except Exception:
                continue

            if qdata is None:
                break  # stop sentinel

            question = qdata.get("question", "")
            options: list[str] = qdata.get("options", [])

            # print question
            print(f"\n{'=' * 60}", flush=True)
            print(f"[HermitAgent question]\n{question}", flush=True)
            if options:
                print("", flush=True)
                for i, opt in enumerate(options, 1):
                    print(f"  {i}. {opt}", flush=True)
            print("=" * 60, flush=True)

            # collect answer
            try:
                answer = input("Answer: ").strip()
            except (EOFError, KeyboardInterrupt):
                answer = "skip"

            self.reply_queue.put(answer)

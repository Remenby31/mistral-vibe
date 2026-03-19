"""Tmux terminal backend."""

from __future__ import annotations

import os
import shlex
import subprocess

from vibe.core.ipc.terminal.base import TerminalBackend


class TmuxBackend(TerminalBackend):
    """Spawn sessions in new tmux windows."""

    name = "tmux"

    @classmethod
    def detect(cls) -> bool:
        """Detect via TMUX environment variable."""
        return "TMUX" in os.environ

    def spawn(self, cmd: list[str], title: str, cwd: str | None = None) -> None:
        """Spawn a new tmux window."""
        shell_cmd = shlex.join(cmd)
        args = ["tmux", "new-window", "-n", title]
        if cwd:
            args.extend(["-c", cwd])
        args.append(shell_cmd)
        subprocess.run(args, check=True)  # noqa: S603

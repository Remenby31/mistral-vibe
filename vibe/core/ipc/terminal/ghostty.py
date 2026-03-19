"""Ghostty terminal backend."""

from __future__ import annotations

import os
import shlex
import subprocess

from vibe.core.ipc.terminal.base import TerminalBackend


class GhosttyBackend(TerminalBackend):
    """Spawn sessions in new Ghostty windows."""

    name = "ghostty"

    @classmethod
    def detect(cls) -> bool:
        """Detect via GHOSTTY_RESOURCES_DIR environment variable."""
        return "GHOSTTY_RESOURCES_DIR" in os.environ

    def spawn(self, cmd: list[str], title: str, cwd: str | None = None) -> None:
        """Spawn a new Ghostty window."""
        args = ["ghostty", f"--title={title}"]
        if cwd:
            args.append(f"--working-directory={cwd}")
        # Ghostty -e expects a single command with args; wrap in sh -c for robustness
        shell_cmd = shlex.join(cmd)
        args.extend(["-e", "sh", "-c", shell_cmd])
        subprocess.Popen(args, start_new_session=True)  # noqa: S603

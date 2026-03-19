"""WezTerm terminal backend."""

from __future__ import annotations

import os
import subprocess

from vibe.core.ipc.terminal.base import TerminalBackend


class WeztermBackend(TerminalBackend):
    """Spawn sessions in new WezTerm windows."""

    name = "wezterm"

    @classmethod
    def detect(cls) -> bool:
        """Detect via WEZTERM_PANE environment variable."""
        return "WEZTERM_PANE" in os.environ

    def spawn(self, cmd: list[str], title: str, cwd: str | None = None) -> None:
        """Spawn a new WezTerm window."""
        args = ["wezterm", "cli", "spawn", "--new-window"]
        if cwd:
            args.extend(["--cwd", cwd])
        args.extend(["--", *cmd])
        subprocess.run(args, check=True)  # noqa: S603

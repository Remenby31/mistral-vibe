"""Kitty terminal backend."""

from __future__ import annotations

import os
import subprocess

from vibe.core.ipc.terminal.base import TerminalBackend


class KittyBackend(TerminalBackend):
    """Spawn sessions in new Kitty OS windows via remote control."""

    name = "kitty"

    @classmethod
    def detect(cls) -> bool:
        """Detect via KITTY_PID environment variable."""
        return "KITTY_PID" in os.environ

    def spawn(self, cmd: list[str], title: str, cwd: str | None = None) -> None:
        """Spawn a new Kitty OS window."""
        args = ["kitty", "@", "launch", "--type=os-window", "--title", title]
        if cwd:
            args.extend(["--cwd", cwd])
        args.extend(cmd)
        subprocess.run(args, capture_output=True, text=True, check=True)  # noqa: S603

"""Xterm terminal backend (fallback)."""

from __future__ import annotations

import shutil
import subprocess

from vibe.core.ipc.terminal.base import TerminalBackend


class XtermBackend(TerminalBackend):
    """Spawn sessions in new xterm windows. Used as fallback."""

    name = "xterm"

    @classmethod
    def detect(cls) -> bool:
        """Detect via binary availability."""
        return shutil.which("xterm") is not None

    def spawn(self, cmd: list[str], title: str, cwd: str | None = None) -> None:
        """Spawn a new xterm window."""
        args = ["xterm", "-T", title, "-e", *cmd]
        subprocess.Popen(args, cwd=cwd, start_new_session=True)  # noqa: S603

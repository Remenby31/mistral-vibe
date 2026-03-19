"""GNOME Terminal backend."""

from __future__ import annotations

import shutil
import subprocess

from vibe.core.ipc.terminal.base import TerminalBackend


class GnomeTerminalBackend(TerminalBackend):
    """Spawn sessions in new GNOME Terminal windows."""

    name = "gnome-terminal"

    @classmethod
    def detect(cls) -> bool:
        """Detect via binary availability."""
        return shutil.which("gnome-terminal") is not None

    def spawn(self, cmd: list[str], title: str, cwd: str | None = None) -> None:
        """Spawn a new GNOME Terminal window."""
        args = ["gnome-terminal", f"--title={title}"]
        if cwd:
            args.extend([f"--working-directory={cwd}"])
        args.extend(["--", *cmd])
        subprocess.Popen(args, start_new_session=True)  # noqa: S603

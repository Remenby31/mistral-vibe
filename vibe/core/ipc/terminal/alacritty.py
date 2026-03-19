"""Alacritty terminal backend."""

from __future__ import annotations

import os
import shutil
import subprocess

from vibe.core.ipc.terminal.base import TerminalBackend


class AlacrittyBackend(TerminalBackend):
    """Spawn sessions in new Alacritty windows."""

    name = "alacritty"

    @classmethod
    def detect(cls) -> bool:
        """Detect via TERM or binary availability."""
        return os.environ.get("TERM", "").startswith("alacritty") or shutil.which("alacritty") is not None

    def spawn(self, cmd: list[str], title: str, cwd: str | None = None) -> None:
        """Spawn a new Alacritty window."""
        args = ["alacritty", "--title", title]
        if cwd:
            args.extend(["--working-directory", cwd])
        args.extend(["-e", *cmd])
        subprocess.Popen(args, start_new_session=True)  # noqa: S603

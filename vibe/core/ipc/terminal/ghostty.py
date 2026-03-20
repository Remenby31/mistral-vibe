"""Ghostty terminal backend."""

from __future__ import annotations

import os
import platform
import shlex
import subprocess

from vibe.core.ipc.terminal.base import TerminalBackend

_GHOSTTY_MACOS_BIN = "/Applications/Ghostty.app/Contents/MacOS/ghostty"


class GhosttyBackend(TerminalBackend):
    """Spawn sessions in new Ghostty windows."""

    name = "ghostty"

    @classmethod
    def detect(cls) -> bool:
        """Detect via GHOSTTY_RESOURCES_DIR environment variable."""
        return "GHOSTTY_RESOURCES_DIR" in os.environ

    def spawn(self, cmd: list[str], title: str, cwd: str | None = None) -> None:
        """Spawn a new Ghostty window."""
        shell_cmd = shlex.join(cmd)
        cd_part = f"cd {shlex.quote(cwd)} && " if cwd else ""
        full_cmd = f"{cd_part}{shell_cmd}"

        if platform.system() == "Darwin" and os.path.isfile(_GHOSTTY_MACOS_BIN):
            # On macOS, the `ghostty` CLI broadcasts -e commands to ALL
            # existing windows, multiplying spawns by the open window count.
            # Calling the app binary directly with --command opens exactly
            # one new window per invocation.
            args = [
                _GHOSTTY_MACOS_BIN,
                f"--command=sh -c {shlex.quote(full_cmd)}",
                f"--title={title}",
            ]
            if cwd:
                args.append(f"--working-directory={cwd}")
        else:
            args = ["ghostty", f"--title={title}"]
            if cwd:
                args.append(f"--working-directory={cwd}")
            args.extend(["-e", "sh", "-c", shell_cmd])

        subprocess.Popen(args, start_new_session=True)  # noqa: S603

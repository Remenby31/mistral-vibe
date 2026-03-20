"""Ghostty terminal backend."""

from __future__ import annotations

import os
import platform
import shlex
import subprocess

from vibe.core.ipc.terminal.base import TerminalBackend


_CASCADE_OFFSET = 30  # pixels offset per agent window


class GhosttyBackend(TerminalBackend):
    """Spawn sessions in new Ghostty windows."""

    name = "ghostty"
    _spawn_count: int = 1

    @classmethod
    def detect(cls) -> bool:
        """Detect via GHOSTTY_RESOURCES_DIR environment variable."""
        return "GHOSTTY_RESOURCES_DIR" in os.environ

    def spawn(self, cmd: list[str], title: str, cwd: str | None = None) -> None:
        """Spawn a new Ghostty window."""
        shell_cmd = shlex.join(cmd)
        cd_part = f"cd {shlex.quote(cwd)} && " if cwd else ""
        full_cmd = f"{cd_part}{shell_cmd}"

        if platform.system() == "Darwin":
            self._spawn_macos(full_cmd, title)
            self._spawn_count += 1
        else:
            args = ["ghostty", f"--title={title}"]
            if cwd:
                args.append(f"--working-directory={cwd}")
            args.extend(["-e", "sh", "-c", shell_cmd])
            subprocess.Popen(args, start_new_session=True)  # noqa: S603

    def _spawn_macos(self, full_cmd: str, title: str) -> None:
        """Spawn a new Ghostty window on macOS using native AppleScript.

        Uses Ghostty's native AppleScript API (1.3+) to create windows
        within the existing Ghostty process. This avoids the broadcast
        bug where `ghostty -e` multiplies commands across all windows.
        After spawning, the parent window is raised back to front.
        """
        # Escape for AppleScript string (backslashes and quotes)
        escaped_cmd = full_cmd.replace("\\", "\\\\").replace('"', '\\"')
        escaped_title = title.replace("\\", "\\\\").replace('"', '\\"')

        applescript = f'''
tell application "Ghostty"
    set cfg to new surface configuration
    set w to new window with configuration cfg
    set t to focused terminal of selected tab of w
    input text "{escaped_cmd}" to t
    send key "enter" to t
end tell

tell application "System Events"
    tell process "Ghostty"
        -- Position agent at same location as the frontmost Claude/Vibe window
        set parentWindow to missing value
        repeat with w in (every window)
            set n to name of w
            if n contains "Claude" or n contains "Vibe" then
                set parentWindow to w
                exit repeat
            end if
        end repeat

        if parentWindow is not missing value then
            set parentPos to position of parentWindow
            set parentSize to size of parentWindow
            set offsetX to {self._spawn_count * _CASCADE_OFFSET}
            set offsetY to -{self._spawn_count * _CASCADE_OFFSET}
            -- Find the newly created window (last one without Claude/Vibe in title)
            set allWindows to every window
            repeat with w in allWindows
                set n to name of w
                if n does not contain "Claude" and n does not contain "Vibe" then
                    set position of w to {{(item 1 of parentPos) + offsetX, (item 2 of parentPos) + offsetY}}
                    set size of w to parentSize
                end if
            end repeat

            -- Raise parent back to front
            perform action "AXRaise" of parentWindow
        end if
    end tell
end tell
'''
        subprocess.Popen(  # noqa: S603
            ["osascript", "-e", applescript],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

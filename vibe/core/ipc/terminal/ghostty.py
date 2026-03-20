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

        The cascade offset is computed inside AppleScript by counting
        existing agent windows, so it works correctly even with parallel
        spawns or when the caller doesn't know its own index.
        """
        # Escape for AppleScript string (backslashes and quotes)
        escaped_cmd = full_cmd.replace("\\", "\\\\").replace('"', '\\"')

        applescript = f'''
-- Snapshot state before creating the new window
tell application "System Events"
    tell process "Ghostty"
        set agentCount to 0
        repeat with w in (every window)
            set n to name of w
            if n does not contain "Claude" and n does not contain "Vibe" then
                set agentCount to agentCount + 1
            end if
        end repeat
        set windowsBefore to id of every window
    end tell
end tell

-- Create the new window via Ghostty AppleScript API
tell application "Ghostty"
    set cfg to new surface configuration
    set w to new window with configuration cfg
    set t to focused terminal of selected tab of w
    input text "{escaped_cmd}" to t
    send key "enter" to t
end tell

delay 0.3

-- Position only the NEW window
tell application "System Events"
    tell process "Ghostty"
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
            set cascadeIndex to agentCount + 1
            set offsetX to cascadeIndex * {_CASCADE_OFFSET}
            set offsetY to -(cascadeIndex * {_CASCADE_OFFSET})

            repeat with w in (every window)
                if (id of w) is not in windowsBefore then
                    set position of w to {{(item 1 of parentPos) + offsetX, (item 2 of parentPos) + offsetY}}
                    set size of w to parentSize
                    exit repeat
                end if
            end repeat
        end if
    end tell
end tell

'''
        subprocess.run(  # noqa: S603
            ["osascript", "-e", applescript],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Refocus parent in a separate osascript call — must be separate
        # because Ghostty re-focuses the new window at the end of the
        # creation script, overriding any activate within the same script.
        refocus = '''
tell application "Ghostty"
    repeat with w in (every window)
        if name of w contains "Claude" or name of w contains "Vibe" then
            activate window w
            exit repeat
        end if
    end repeat
end tell
'''
        subprocess.run(  # noqa: S603
            ["osascript", "-e", refocus],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

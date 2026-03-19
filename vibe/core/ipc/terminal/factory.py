"""Terminal backend auto-detection and factory."""

from __future__ import annotations

import logging

from vibe.core.ipc.terminal.base import TerminalBackend
from vibe.core.ipc.terminal.kitty import KittyBackend
from vibe.core.ipc.terminal.tmux import TmuxBackend
from vibe.core.ipc.terminal.wezterm import WeztermBackend
from vibe.core.ipc.terminal.alacritty import AlacrittyBackend
from vibe.core.ipc.terminal.gnome_terminal import GnomeTerminalBackend
from vibe.core.ipc.terminal.xterm import XtermBackend

logger = logging.getLogger(__name__)

# Ordered by preference — more feature-rich terminals first
BACKENDS: list[type[TerminalBackend]] = [
    KittyBackend,
    WeztermBackend,
    TmuxBackend,
    AlacrittyBackend,
    GnomeTerminalBackend,
    XtermBackend,
]

_BACKEND_MAP: dict[str, type[TerminalBackend]] = {b.name: b for b in BACKENDS}


class NoTerminalBackendError(RuntimeError):
    """No supported terminal backend found."""


def detect_backend(override: str | None = None) -> TerminalBackend:
    """Detect and return the appropriate terminal backend.

    Args:
        override: Force a specific backend by name (e.g. "kitty", "tmux").
                  Set via config `agentree.terminal_backend`.
    """
    if override:
        cls = _BACKEND_MAP.get(override)
        if cls is None:
            msg = f"Unknown terminal backend '{override}'. Available: {', '.join(_BACKEND_MAP)}"
            raise NoTerminalBackendError(msg)
        logger.info("Using configured terminal backend: %s", override)
        return cls()

    for cls in BACKENDS:
        if cls.detect():
            logger.info("Auto-detected terminal backend: %s", cls.name)
            return cls()

    supported = ", ".join(b.name for b in BACKENDS)
    msg = f"No supported terminal detected. Supported: {supported}"
    raise NoTerminalBackendError(msg)

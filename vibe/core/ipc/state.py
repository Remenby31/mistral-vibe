"""Global agentree state — single source of truth for IPC mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibe.core.ipc.server import IPCServer

_enabled: bool = False
_ipc_server: IPCServer | None = None
_parent_pid: int | None = None


def is_enabled() -> bool:
    """Whether agentree mode is currently active."""
    return _enabled


def enable(server: IPCServer, parent_pid: int | None = None) -> None:
    """Activate agentree mode."""
    global _enabled, _ipc_server, _parent_pid  # noqa: PLW0603
    _enabled = True
    _ipc_server = server
    _parent_pid = parent_pid


def disable() -> None:
    """Deactivate agentree mode."""
    global _enabled, _ipc_server, _parent_pid  # noqa: PLW0603
    _enabled = False
    _ipc_server = None
    _parent_pid = None


def get_server() -> IPCServer | None:
    """Get the current IPC server, if any."""
    return _ipc_server


def get_parent_pid() -> int | None:
    """Get the parent PID if this session was spawned by another."""
    return _parent_pid

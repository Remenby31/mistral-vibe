"""Abstract base class for terminal backends."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TerminalBackend(ABC):
    """Interface for spawning vibe sessions in new terminal windows.

    Backends launch a command in a new terminal window. The actual PID of the
    vibe child process is obtained separately via a pid file written by the child
    at startup, since not all terminals expose the PID of the inner process.
    """

    name: str = "unknown"

    @classmethod
    @abstractmethod
    def detect(cls) -> bool:
        """Return True if this terminal backend is available."""
        ...

    @abstractmethod
    def spawn(self, cmd: list[str], title: str, cwd: str | None = None) -> None:
        """Open a new terminal window running cmd."""
        ...

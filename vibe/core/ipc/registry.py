"""Agentree session registry with file locking and self-healing."""

from __future__ import annotations

import fcntl
import json
import logging
import os
from pathlib import Path

from vibe.core.ipc.types import RegistryEntry

logger = logging.getLogger(__name__)

IPC_DIR = Path.home() / ".vibe" / "ipc"
REGISTRY_PATH = IPC_DIR / "registry.json"


def _is_pid_alive(pid: int) -> bool:
    """Check if a process is alive via signal 0."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # process exists but we can't signal it
    return True


class AgentreeRegistry:
    """File-backed registry of active agentree sessions.

    Uses fcntl.flock for concurrent access safety and self-heals
    by purging entries with dead PIDs on every read.
    """

    def __init__(self, registry_path: Path = REGISTRY_PATH) -> None:
        self._path = registry_path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def register(self, entry: RegistryEntry) -> None:
        """Register a session in the registry."""
        with self._locked_access() as entries:
            # Remove any existing entry with same PID
            entries = [e for e in entries if e.pid != entry.pid]
            entries.append(entry)
            self._write(entries)

    def unregister(self, pid: int) -> None:
        """Remove a session from the registry by PID."""
        with self._locked_access() as entries:
            entries = [e for e in entries if e.pid != pid]
            self._write(entries)

    def list_sessions(self) -> list[RegistryEntry]:
        """List all active sessions, purging dead ones."""
        with self._locked_access() as entries:
            alive = [e for e in entries if _is_pid_alive(e.pid)]
            if len(alive) != len(entries):
                dead_pids = {e.pid for e in entries} - {e.pid for e in alive}
                logger.info("Purged dead sessions from registry: %s", dead_pids)
                self._write(alive)
            return alive

    def get_session(self, pid: int) -> RegistryEntry | None:
        """Get a session by PID, or None if not found/dead."""
        for entry in self.list_sessions():
            if entry.pid == pid:
                return entry
        return None

    def _locked_access(self) -> _RegistryLock:
        """Context manager for locked file access."""
        return _RegistryLock(self._path)

    def _write(self, entries: list[RegistryEntry]) -> None:
        """Write entries to registry file (must be called within lock)."""
        self._path.write_text(json.dumps([e.to_dict() for e in entries], indent=2))


class _RegistryLock:
    """Context manager that locks the registry file and yields parsed entries."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    def __enter__(self) -> list[RegistryEntry]:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]")
        self._fd = os.open(str(self._path), os.O_RDWR)
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        try:
            raw = os.read(self._fd, 1024 * 1024).decode()
            data = json.loads(raw) if raw.strip() else []
            return [RegistryEntry.from_dict(d) for d in data]
        except (json.JSONDecodeError, KeyError):
            logger.warning("Corrupted registry file, resetting")
            return []

    def __exit__(self, *_args: object) -> None:
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)

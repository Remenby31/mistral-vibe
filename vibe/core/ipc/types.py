"""IPC message types for agentree inter-session communication."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class IPCRequest:
    """JSON-RPC request sent over UDS."""

    method: str
    params: dict[str, object] = field(default_factory=dict)
    id: str | None = None  # None = notification (no response expected)

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-RPC dict."""
        d: dict[str, object] = {"jsonrpc": "2.0", "method": self.method, "params": self.params}
        if self.id is not None:
            d["id"] = self.id
        return d

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> IPCRequest:
        """Deserialize from JSON-RPC dict."""
        return cls(
            method=str(data.get("method", "")),
            params=dict(data.get("params", {})),  # type: ignore[arg-type]
            id=data.get("id"),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class IPCResponse:
    """JSON-RPC response sent over UDS."""

    id: str
    result: dict[str, object] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize to JSON-RPC dict."""
        d: dict[str, object] = {"jsonrpc": "2.0", "id": self.id}
        if self.error is not None:
            d["error"] = {"message": self.error}
        else:
            d["result"] = self.result or {}
        return d

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> IPCResponse:
        """Deserialize from JSON-RPC dict."""
        error_obj = data.get("error")
        error_msg = None
        if isinstance(error_obj, dict):
            error_msg = str(error_obj.get("message", "Unknown error"))
        return cls(
            id=str(data.get("id", "")),
            result=data.get("result"),  # type: ignore[arg-type]
            error=error_msg,
        )


@dataclass
class RegistryEntry:
    """A session registered in the agentree registry."""

    pid: int
    session_id: str
    socket_path: str
    cwd: str
    parent_pid: int | None = None
    started_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict for JSON storage."""
        return {
            "pid": self.pid,
            "session_id": self.session_id,
            "socket_path": self.socket_path,
            "cwd": self.cwd,
            "parent_pid": self.parent_pid,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> RegistryEntry:
        """Deserialize from dict."""
        return cls(
            pid=int(data["pid"]),  # type: ignore[arg-type]
            session_id=str(data["session_id"]),
            socket_path=str(data["socket_path"]),
            cwd=str(data["cwd"]),
            parent_pid=int(data["parent_pid"]) if data.get("parent_pid") is not None else None,  # type: ignore[arg-type]
            started_at=float(data.get("started_at", 0)),  # type: ignore[arg-type]
        )

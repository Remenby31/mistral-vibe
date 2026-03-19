"""Async Unix Domain Socket client for agentree IPC."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

from vibe.core.ipc.types import IPCRequest, IPCResponse

logger = logging.getLogger(__name__)

TIMEOUT = 5.0


async def send_message(socket_path: str, sender_pid: int, content: str) -> bool:
    """Send a message to another session via its UDS socket."""
    request = IPCRequest(
        method="send_message",
        params={"sender_pid": sender_pid, "content": content},
        id=uuid.uuid4().hex[:8],
    )
    response = await _send_request(socket_path, request)
    if response is None:
        return False
    return response.error is None


async def read_messages(socket_path: str, last_n: int = 10) -> list[str]:
    """Read the last N assistant messages from another session."""
    request = IPCRequest(
        method="read_messages",
        params={"last_n": last_n},
        id=uuid.uuid4().hex[:8],
    )
    response = await _send_request(socket_path, request)
    if response is None or response.error or response.result is None:
        return []
    return list(response.result.get("messages", []))  # type: ignore[arg-type]


async def request_shutdown(socket_path: str) -> bool:
    """Request a session to shutdown gracefully."""
    request = IPCRequest(
        method="shutdown",
        params={},
        id=uuid.uuid4().hex[:8],
    )
    response = await _send_request(socket_path, request)
    if response is None:
        return False
    return response.error is None


async def _send_request(socket_path: str, request: IPCRequest) -> IPCResponse | None:
    """Send a JSON-RPC request and receive the response."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_unix_connection(socket_path),
            timeout=TIMEOUT,
        )
    except (TimeoutError, ConnectionRefusedError, FileNotFoundError) as e:
        logger.warning("Failed to connect to %s: %s", socket_path, e)
        return None

    try:
        writer.write(json.dumps(request.to_dict()).encode())
        await writer.drain()

        if request.id is None:
            return None

        data = await asyncio.wait_for(reader.read(1024 * 1024), timeout=TIMEOUT)
        if not data:
            return None
        return IPCResponse.from_dict(json.loads(data.decode()))
    except (TimeoutError, json.JSONDecodeError) as e:
        logger.warning("IPC request failed for %s: %s", socket_path, e)
        return None
    finally:
        writer.close()
        await writer.wait_closed()

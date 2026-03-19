"""Async Unix Domain Socket server for agentree IPC."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from vibe.core.ipc.types import IPCRequest, IPCResponse

logger = logging.getLogger(__name__)

IPC_DIR = Path.home() / ".vibe" / "ipc"


class IPCServer:
    """UDS server that handles incoming JSON-RPC messages for a vibe session.

    Incoming messages are queued and drained by the agent loop before each turn.
    Also supports read_messages requests so other sessions can pull conversation history.
    """

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._socket_path = IPC_DIR / f"sock_{session_id}.sock"
        self._server: asyncio.Server | None = None
        self._message_queue: asyncio.Queue[tuple[int, str]] = asyncio.Queue()
        self._shutdown_event = asyncio.Event()
        self._assistant_messages: list[str] = []
        self._max_stored_messages = 200

    @property
    def socket_path(self) -> str:
        """Path to the UDS socket file."""
        return str(self._socket_path)

    @property
    def shutdown_requested(self) -> bool:
        """Whether a shutdown has been requested via IPC."""
        return self._shutdown_event.is_set()

    def record_assistant_message(self, message: str) -> None:
        """Record an assistant message for read_messages requests."""
        self._assistant_messages.append(message)
        if len(self._assistant_messages) > self._max_stored_messages:
            self._assistant_messages = self._assistant_messages[-self._max_stored_messages :]

    def drain_messages(self) -> list[tuple[int, str]]:
        """Drain all pending IPC messages. Returns list of (sender_pid, content)."""
        messages = []
        while not self._message_queue.empty():
            try:
                messages.append(self._message_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return messages

    async def start(self) -> None:
        """Start the UDS server."""
        IPC_DIR.mkdir(parents=True, exist_ok=True)
        # Clean up stale socket
        if self._socket_path.exists():
            self._socket_path.unlink()
        self._server = await asyncio.start_unix_server(self._handle_client, path=str(self._socket_path))
        logger.info("IPC server started at %s", self._socket_path)

    async def stop(self) -> None:
        """Stop the server and clean up the socket file."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._socket_path.exists():
            self._socket_path.unlink()
        logger.info("IPC server stopped")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle a single client connection."""
        try:
            data = await asyncio.wait_for(reader.read(1024 * 1024), timeout=10.0)
            if not data:
                return

            request = IPCRequest.from_dict(json.loads(data.decode()))
            response = await self._dispatch(request)

            if response and request.id is not None:
                writer.write(json.dumps(response.to_dict()).encode())
                await writer.drain()
        except TimeoutError:
            logger.warning("IPC client connection timed out")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Invalid IPC message: %s", e)
        finally:
            writer.close()
            await writer.wait_closed()

    async def _dispatch(self, request: IPCRequest) -> IPCResponse | None:
        """Dispatch a JSON-RPC request to the appropriate handler."""
        if request.method == "send_message":
            return self._handle_send_message(request)
        if request.method == "read_messages":
            return self._handle_read_messages(request)
        if request.method == "shutdown":
            return self._handle_shutdown(request)
        if request.id:
            return IPCResponse(id=request.id, error=f"Unknown method: {request.method}")
        return None

    def _handle_send_message(self, request: IPCRequest) -> IPCResponse | None:
        """Queue an incoming message from another session."""
        sender_pid = int(request.params.get("sender_pid", 0))
        content = str(request.params.get("content", ""))
        if not content:
            if request.id:
                return IPCResponse(id=request.id, error="Empty message")
            return None
        self._message_queue.put_nowait((sender_pid, content))
        if request.id:
            return IPCResponse(id=request.id, result={"ack": True})
        return None

    def _handle_read_messages(self, request: IPCRequest) -> IPCResponse | None:
        """Return the last N assistant messages."""
        last_n = int(request.params.get("last_n", 10))
        messages = self._assistant_messages[-last_n:]
        if request.id:
            return IPCResponse(id=request.id, result={"messages": messages, "pid": os.getpid()})
        return None

    def _handle_shutdown(self, request: IPCRequest) -> IPCResponse | None:
        """Set the shutdown flag."""
        self._shutdown_event.set()
        logger.info("Shutdown requested via IPC")
        if request.id:
            return IPCResponse(id=request.id, result={"ack": True})
        return None

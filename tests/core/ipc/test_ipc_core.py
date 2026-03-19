"""Tests for IPC infrastructure: types, registry, server, client."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from vibe.core.ipc.types import IPCRequest, IPCResponse, RegistryEntry
from vibe.core.ipc.registry import AgentreeRegistry
from vibe.core.ipc.server import IPCServer
from vibe.core.ipc import client as ipc_client


# --- Types ---


class TestIPCRequest:
    def test_roundtrip(self) -> None:
        req = IPCRequest(method="send_message", params={"text": "hello"}, id="abc")
        d = req.to_dict()
        assert d["jsonrpc"] == "2.0"
        restored = IPCRequest.from_dict(d)
        assert restored.method == "send_message"
        assert restored.params["text"] == "hello"
        assert restored.id == "abc"

    def test_notification_no_id(self) -> None:
        req = IPCRequest(method="ping", params={})
        d = req.to_dict()
        assert "id" not in d


class TestIPCResponse:
    def test_success_roundtrip(self) -> None:
        resp = IPCResponse(id="1", result={"ack": True})
        d = resp.to_dict()
        restored = IPCResponse.from_dict(d)
        assert restored.result == {"ack": True}
        assert restored.error is None

    def test_error_roundtrip(self) -> None:
        resp = IPCResponse(id="1", error="bad request")
        d = resp.to_dict()
        restored = IPCResponse.from_dict(d)
        assert restored.error == "bad request"


class TestRegistryEntry:
    def test_roundtrip(self) -> None:
        entry = RegistryEntry(pid=1234, session_id="abc", socket_path="/tmp/s.sock", cwd="/home")
        d = entry.to_dict()
        restored = RegistryEntry.from_dict(d)
        assert restored.pid == 1234
        assert restored.parent_pid is None

    def test_with_parent(self) -> None:
        entry = RegistryEntry(pid=1234, session_id="abc", socket_path="/tmp/s.sock", cwd="/home", parent_pid=5678)
        d = entry.to_dict()
        restored = RegistryEntry.from_dict(d)
        assert restored.parent_pid == 5678


# --- Registry ---


class TestAgentreeRegistry:
    def test_register_and_list(self, tmp_path: Path) -> None:
        registry = AgentreeRegistry(tmp_path / "registry.json")
        entry = RegistryEntry(pid=os.getpid(), session_id="s1", socket_path="/tmp/s.sock", cwd="/home")
        registry.register(entry)
        sessions = registry.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].session_id == "s1"

    def test_unregister(self, tmp_path: Path) -> None:
        registry = AgentreeRegistry(tmp_path / "registry.json")
        entry = RegistryEntry(pid=os.getpid(), session_id="s1", socket_path="/tmp/s.sock", cwd="/home")
        registry.register(entry)
        registry.unregister(os.getpid())
        assert len(registry.list_sessions()) == 0

    def test_self_healing_purges_dead_pids(self, tmp_path: Path) -> None:
        registry = AgentreeRegistry(tmp_path / "registry.json")
        # PID 99999999 is almost certainly dead
        entry = RegistryEntry(pid=99999999, session_id="dead", socket_path="/tmp/s.sock", cwd="/home")
        registry.register(entry)
        sessions = registry.list_sessions()
        assert len(sessions) == 0

    def test_get_session(self, tmp_path: Path) -> None:
        registry = AgentreeRegistry(tmp_path / "registry.json")
        entry = RegistryEntry(pid=os.getpid(), session_id="s1", socket_path="/tmp/s.sock", cwd="/home")
        registry.register(entry)
        found = registry.get_session(os.getpid())
        assert found is not None
        assert found.session_id == "s1"
        assert registry.get_session(99999999) is None


# --- Server + Client ---


class TestIPCServerClient:
    @pytest.mark.asyncio
    async def test_send_and_drain_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server = IPCServer("test_session")
            server._socket_path = Path(tmpdir) / "test.sock"
            await server.start()
            try:
                result = await ipc_client.send_message(str(server._socket_path), sender_pid=1234, content="hello")
                assert result is True

                messages = server.drain_messages()
                assert len(messages) == 1
                assert messages[0] == (1234, "hello")

                # Queue should be empty now
                assert len(server.drain_messages()) == 0
            finally:
                await server.stop()

    @pytest.mark.asyncio
    async def test_read_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server = IPCServer("test_session")
            server._socket_path = Path(tmpdir) / "test.sock"
            await server.start()
            try:
                server.record_assistant_message("msg1")
                server.record_assistant_message("msg2")
                server.record_assistant_message("msg3")

                messages = await ipc_client.read_messages(str(server._socket_path), last_n=2)
                assert messages == ["msg2", "msg3"]
            finally:
                await server.stop()

    @pytest.mark.asyncio
    async def test_shutdown_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            server = IPCServer("test_session")
            server._socket_path = Path(tmpdir) / "test.sock"
            await server.start()
            try:
                assert not server.shutdown_requested
                result = await ipc_client.request_shutdown(str(server._socket_path))
                assert result is True
                assert server.shutdown_requested
            finally:
                await server.stop()

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_socket(self) -> None:
        result = await ipc_client.send_message("/tmp/nonexistent.sock", sender_pid=1, content="hello")
        assert result is False

    @pytest.mark.asyncio
    async def test_read_from_nonexistent_socket(self) -> None:
        messages = await ipc_client.read_messages("/tmp/nonexistent.sock")
        assert messages == []

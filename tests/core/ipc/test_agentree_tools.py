"""Tests for agentree tools visibility and state toggling."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from vibe.core.ipc import state as agentree_state
from vibe.core.ipc.server import IPCServer
from vibe.core.tools.builtins.agentree.spawn_session import SpawnSession
from vibe.core.tools.builtins.agentree.send_message import SendMessage
from vibe.core.tools.builtins.agentree.read_session import ReadSession
from vibe.core.tools.builtins.agentree.list_sessions import ListSessions
from vibe.core.tools.builtins.agentree.kill_session import KillSession
from vibe.core.tools.builtins.task import Task

AGENTREE_TOOLS = [SpawnSession, SendMessage, ReadSession, ListSessions, KillSession]


class TestAgentreeState:
    def setup_method(self) -> None:
        agentree_state.disable()

    def teardown_method(self) -> None:
        agentree_state.disable()

    def test_default_disabled(self) -> None:
        assert agentree_state.is_enabled() is False
        assert agentree_state.get_server() is None
        assert agentree_state.get_parent_pid() is None

    def test_enable_disable(self) -> None:
        server = IPCServer("test")
        agentree_state.enable(server, parent_pid=1234)
        assert agentree_state.is_enabled() is True
        assert agentree_state.get_server() is server
        assert agentree_state.get_parent_pid() == 1234

        agentree_state.disable()
        assert agentree_state.is_enabled() is False
        assert agentree_state.get_server() is None


class TestToolVisibility:
    def setup_method(self) -> None:
        agentree_state.disable()

    def teardown_method(self) -> None:
        agentree_state.disable()

    def test_agentree_tools_hidden_when_disabled(self) -> None:
        for tool_cls in AGENTREE_TOOLS:
            assert tool_cls.is_available() is False, f"{tool_cls.__name__} should be hidden"

    def test_agentree_tools_visible_when_enabled(self) -> None:
        server = IPCServer("test")
        agentree_state.enable(server)
        for tool_cls in AGENTREE_TOOLS:
            assert tool_cls.is_available() is True, f"{tool_cls.__name__} should be visible"

    def test_task_tool_visible_when_disabled(self) -> None:
        assert Task.is_available() is True

    def test_task_tool_hidden_when_enabled(self) -> None:
        server = IPCServer("test")
        agentree_state.enable(server)
        assert Task.is_available() is False


class TestSpawnSessionPromptBuilder:
    def test_build_prompt_no_files(self) -> None:
        from vibe.core.tools.builtins.agentree.spawn_session import SpawnSessionConfig

        tool = SpawnSession(config=SpawnSessionConfig(), state=None)  # type: ignore[arg-type]
        result = tool._build_prompt("Do something", None)
        assert result == "Do something"

    def test_build_prompt_with_files(self, tmp_path: Path) -> None:
        from vibe.core.tools.builtins.agentree.spawn_session import SpawnSessionConfig

        f1 = tmp_path / "file1.txt"
        f1.write_text("content1")
        f2 = tmp_path / "file2.txt"
        f2.write_text("content2")

        tool = SpawnSession(config=SpawnSessionConfig(), state=None)  # type: ignore[arg-type]
        result = tool._build_prompt("Do something", [str(f1), str(f2)])
        assert "<context>" in result
        assert "content1" in result
        assert "content2" in result
        assert "Do something" in result

    def test_build_prompt_missing_file(self) -> None:
        from vibe.core.tools.builtins.agentree.spawn_session import SpawnSessionConfig

        tool = SpawnSession(config=SpawnSessionConfig(), state=None)  # type: ignore[arg-type]
        result = tool._build_prompt("Do something", ["/nonexistent/file.txt"])
        assert "(not found)" in result

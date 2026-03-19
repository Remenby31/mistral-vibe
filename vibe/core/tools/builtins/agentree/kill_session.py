"""Tool to kill an agentree session."""

from __future__ import annotations

import asyncio
import os
import signal
from collections.abc import AsyncGenerator
from typing import ClassVar

from pydantic import BaseModel, Field

from vibe.core.ipc import client as ipc_client
from vibe.core.ipc import state as agentree_state
from vibe.core.ipc.registry import AgentreeRegistry
from vibe.core.tools.base import (
    BaseTool,
    BaseToolConfig,
    BaseToolState,
    InvokeContext,
    ToolError,
    ToolPermission,
)
from vibe.core.tools.ui import ToolCallDisplay, ToolResultDisplay, ToolUIData
from vibe.core.types import ToolCallEvent, ToolResultEvent, ToolStreamEvent


class KillSessionArgs(BaseModel):
    """Arguments for killing a session."""

    pid: int = Field(description="PID of the agent session to kill")


class KillSessionResult(BaseModel):
    """Result of killing a session."""

    success: bool = Field(description="Whether the session was killed")
    message: str = Field(description="Status message")


class KillSessionConfig(BaseToolConfig):
    """Config for kill_session tool."""

    permission: ToolPermission = ToolPermission.ALWAYS


class KillSession(
    BaseTool[KillSessionArgs, KillSessionResult, KillSessionConfig, BaseToolState],
    ToolUIData[KillSessionArgs, KillSessionResult],
):
    """Kill an agentree session gracefully."""

    description: ClassVar[str] = (
        "Kill an agent session by PID. Sends a graceful shutdown request first, "
        "then forces termination if needed. The terminal window will close."
    )

    @classmethod
    def is_available(cls) -> bool:
        """Only available when agentree mode is enabled."""
        return agentree_state.is_enabled()

    @classmethod
    def get_call_display(cls, event: ToolCallEvent) -> ToolCallDisplay:
        """Display info for the tool call."""
        args = event.args
        if isinstance(args, KillSessionArgs):
            return ToolCallDisplay(summary=f"Killing pid:{args.pid}")
        return ToolCallDisplay(summary="Killing session")

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        """Display info for the tool result."""
        result = event.result
        if isinstance(result, KillSessionResult):
            return ToolResultDisplay(success=result.success, message=result.message)
        return ToolResultDisplay(success=True, message="Done")

    @classmethod
    def get_status_text(cls) -> str:
        """Status text shown during execution."""
        return "Killing session..."

    async def run(
        self, args: KillSessionArgs, ctx: InvokeContext | None = None
    ) -> AsyncGenerator[ToolStreamEvent | KillSessionResult, None]:
        """Kill a session gracefully, then forcefully if needed."""
        registry = AgentreeRegistry()
        session = registry.get_session(args.pid)

        if session is None:
            raise ToolError(f"No active session with pid:{args.pid}")

        # Try graceful shutdown via IPC
        shutdown_ok = await ipc_client.request_shutdown(session.socket_path)
        if shutdown_ok:
            # Wait briefly for the process to exit
            await asyncio.sleep(2.0)

        # Check if still alive, force kill if needed
        try:
            os.kill(args.pid, 0)
            # Still alive — force kill
            os.kill(args.pid, signal.SIGTERM)
            await asyncio.sleep(0.5)
            try:
                os.kill(args.pid, 0)
                os.kill(args.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        except ProcessLookupError:
            pass  # Already dead

        registry.unregister(args.pid)
        yield KillSessionResult(success=True, message=f"Session pid:{args.pid} terminated")

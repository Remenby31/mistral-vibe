"""Tool to list all active agentree sessions."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import ClassVar

from pydantic import BaseModel, Field

from vibe.core.ipc import state as agentree_state
from vibe.core.ipc.registry import AgentreeRegistry
from vibe.core.tools.base import (
    BaseTool,
    BaseToolConfig,
    BaseToolState,
    InvokeContext,
    ToolPermission,
)
from vibe.core.tools.ui import ToolCallDisplay, ToolResultDisplay, ToolUIData
from vibe.core.types import ToolCallEvent, ToolResultEvent, ToolStreamEvent


class SessionInfo(BaseModel):
    """Info about an active agentree session."""

    pid: int = Field(description="Process ID")
    session_id: str = Field(description="Session identifier")
    cwd: str = Field(description="Working directory")
    parent_pid: int | None = Field(default=None, description="PID of the spawner, if any")


class ListSessionsArgs(BaseModel):
    """Arguments for listing sessions."""

    only_children: bool = Field(
        default=False,
        description="If true, only list sessions spawned by this agent",
    )


class ListSessionsResult(BaseModel):
    """Result of listing sessions."""

    sessions: list[SessionInfo] = Field(description="Active agentree sessions")


class ListSessionsConfig(BaseToolConfig):
    """Config for list_sessions tool."""

    permission: ToolPermission = ToolPermission.ALWAYS


class ListSessions(
    BaseTool[ListSessionsArgs, ListSessionsResult, ListSessionsConfig, BaseToolState],
    ToolUIData[ListSessionsArgs, ListSessionsResult],
):
    """List all active agentree sessions."""

    description: ClassVar[str] = (
        "List all active agentree sessions with their PIDs, session IDs, "
        "and working directories. Use this to discover which agents are running."
    )

    @classmethod
    def is_available(cls) -> bool:
        """Only available when agentree mode is enabled."""
        return agentree_state.is_enabled()

    @classmethod
    def get_call_display(cls, event: ToolCallEvent) -> ToolCallDisplay:
        """Display info for the tool call."""
        return ToolCallDisplay(summary="Listing agentree sessions")

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        """Display info for the tool result."""
        result = event.result
        if isinstance(result, ListSessionsResult):
            count = len(result.sessions)
            return ToolResultDisplay(success=True, message=f"{count} active session(s)")
        return ToolResultDisplay(success=True, message="Done")

    @classmethod
    def get_status_text(cls) -> str:
        """Status text shown during execution."""
        return "Listing sessions..."

    async def run(
        self, args: ListSessionsArgs, ctx: InvokeContext | None = None
    ) -> AsyncGenerator[ToolStreamEvent | ListSessionsResult, None]:
        """List all active agentree sessions."""
        import os

        registry = AgentreeRegistry()
        entries = registry.list_sessions()

        if args.only_children:
            my_pid = os.getpid()
            entries = [e for e in entries if e.parent_pid == my_pid]

        sessions = [
            SessionInfo(
                pid=e.pid,
                session_id=e.session_id,
                cwd=e.cwd,
                parent_pid=e.parent_pid,
            )
            for e in entries
        ]

        yield ListSessionsResult(sessions=sessions)

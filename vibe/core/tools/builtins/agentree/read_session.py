"""Tool to read recent messages from another agentree session."""

from __future__ import annotations

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


class ReadSessionArgs(BaseModel):
    """Arguments for reading messages from another session."""

    pid: int = Field(description="PID of the target agent session")
    last_n: int = Field(default=10, description="Number of recent assistant messages to retrieve")


class ReadSessionResult(BaseModel):
    """Result of reading session messages."""

    messages: list[str] = Field(description="Recent assistant messages from the session")
    active: bool = Field(description="Whether the session is still active")


class ReadSessionConfig(BaseToolConfig):
    """Config for read_session tool."""

    permission: ToolPermission = ToolPermission.ALWAYS


class ReadSession(
    BaseTool[ReadSessionArgs, ReadSessionResult, ReadSessionConfig, BaseToolState],
    ToolUIData[ReadSessionArgs, ReadSessionResult],
):
    """Read the recent assistant messages from another agentree session."""

    description: ClassVar[str] = (
        "Read the last N assistant messages from another agent session. "
        "Use this to check on an agent's progress or see its results."
    )

    @classmethod
    def is_available(cls) -> bool:
        """Only available when agentree mode is enabled."""
        return agentree_state.is_enabled()

    @classmethod
    def get_call_display(cls, event: ToolCallEvent) -> ToolCallDisplay:
        """Display info for the tool call."""
        args = event.args
        if isinstance(args, ReadSessionArgs):
            return ToolCallDisplay(summary=f"Reading pid:{args.pid} (last {args.last_n})")
        return ToolCallDisplay(summary="Reading session")

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        """Display info for the tool result."""
        result = event.result
        if isinstance(result, ReadSessionResult):
            count = len(result.messages)
            status = "active" if result.active else "inactive"
            return ToolResultDisplay(success=True, message=f"{count} messages ({status})")
        return ToolResultDisplay(success=True, message="Done")

    @classmethod
    def get_status_text(cls) -> str:
        """Status text shown during execution."""
        return "Reading session..."

    async def run(
        self, args: ReadSessionArgs, ctx: InvokeContext | None = None
    ) -> AsyncGenerator[ToolStreamEvent | ReadSessionResult, None]:
        """Read messages from another session via IPC."""
        registry = AgentreeRegistry()
        session = registry.get_session(args.pid)
        if session is None:
            yield ReadSessionResult(messages=[], active=False)
            return

        messages = await ipc_client.read_messages(session.socket_path, last_n=args.last_n)

        yield ReadSessionResult(messages=messages, active=True)

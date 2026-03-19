"""Tool to send a message to another agentree session."""

from __future__ import annotations

import os
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


class SendMessageArgs(BaseModel):
    """Arguments for sending a message to another session."""

    pid: int = Field(description="PID of the target agent session")
    message: str = Field(description="Message text to send")


class SendMessageResult(BaseModel):
    """Result of sending a message."""

    delivered: bool = Field(description="Whether the message was delivered")
    error: str | None = Field(default=None, description="Error message if delivery failed")


class SendMessageConfig(BaseToolConfig):
    """Config for send_message tool."""

    permission: ToolPermission = ToolPermission.ALWAYS


class SendMessage(
    BaseTool[SendMessageArgs, SendMessageResult, SendMessageConfig, BaseToolState],
    ToolUIData[SendMessageArgs, SendMessageResult],
):
    """Send a message to another agentree session by PID."""

    description: ClassVar[str] = (
        "Send a text message to another agent session identified by its PID. "
        "The message will appear in the target agent's conversation."
    )

    @classmethod
    def is_available(cls) -> bool:
        """Only available when agentree mode is enabled."""
        return agentree_state.is_enabled()

    @classmethod
    def get_call_display(cls, event: ToolCallEvent) -> ToolCallDisplay:
        """Display info for the tool call."""
        args = event.args
        if isinstance(args, SendMessageArgs):
            preview = args.message[:50] + "..." if len(args.message) > 50 else args.message
            return ToolCallDisplay(summary=f"Sending to pid:{args.pid}: {preview}")
        return ToolCallDisplay(summary="Sending message")

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        """Display info for the tool result."""
        result = event.result
        if isinstance(result, SendMessageResult):
            if result.delivered:
                return ToolResultDisplay(success=True, message="Message delivered")
            return ToolResultDisplay(success=False, message=result.error or "Delivery failed")
        return ToolResultDisplay(success=True, message="Done")

    @classmethod
    def get_status_text(cls) -> str:
        """Status text shown during execution."""
        return "Sending message..."

    async def run(
        self, args: SendMessageArgs, ctx: InvokeContext | None = None
    ) -> AsyncGenerator[ToolStreamEvent | SendMessageResult, None]:
        """Send a message to another session."""
        registry = AgentreeRegistry()
        session = registry.get_session(args.pid)
        if session is None:
            raise ToolError(f"No active session with pid:{args.pid}")

        delivered = await ipc_client.send_message(
            session.socket_path,
            sender_pid=os.getpid(),
            content=args.message,
        )

        yield SendMessageResult(
            delivered=delivered,
            error=None if delivered else f"Failed to deliver message to pid:{args.pid}",
        )

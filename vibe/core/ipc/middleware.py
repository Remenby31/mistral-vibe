"""Middleware that injects incoming IPC messages as user messages with a structured prefix."""

from __future__ import annotations

from vibe.core.ipc import state as agentree_state
from vibe.core.middleware import (
    ConversationContext,
    MiddlewareAction,
    MiddlewareResult,
    ResetReason,
)
from vibe.core.utils import AGENT_NOTIFICATION_PREFIX


def format_agent_notification(sender_pid: int, notif_type: str, content: str) -> str:
    """Format an agent notification as a prefixed string.

    Format: [agent_notification:PID:TYPE] content
    """
    return f"{AGENT_NOTIFICATION_PREFIX}{sender_pid}:{notif_type}] {content}"


class IPCMessageMiddleware:
    """Drains pending IPC messages and injects them as user messages.

    Each message is formatted with a structured prefix so the TUI can
    render them as dedicated notification widgets instead of plain user messages.
    """

    async def before_turn(self, context: ConversationContext) -> MiddlewareResult:
        """Drain IPC queue and inject as user message if any."""
        server = agentree_state.get_server()
        if server is None:
            return MiddlewareResult()

        messages = server.drain_messages()
        if not messages:
            return MiddlewareResult()

        parts = []
        for sender_pid, content in messages:
            # Parse notification type from prefix like "[idle] ..."
            notif_type = "message"
            notif_content = content
            if content.startswith("[") and "] " in content:
                bracket_end = content.index("] ")
                notif_type = content[1:bracket_end]
                notif_content = content[bracket_end + 2:]

            parts.append(format_agent_notification(sender_pid, notif_type, notif_content))

        return MiddlewareResult(
            action=MiddlewareAction.INJECT_MESSAGE,
            message="\n\n".join(parts),
        )

    def reset(self, reset_reason: ResetReason = ResetReason.STOP) -> None:
        """Nothing to reset."""

"""Tool to spawn a new vibe session in a separate terminal."""

from __future__ import annotations

import os
import sys
import time
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field

from vibe.core.ipc import state as agentree_state
from vibe.core.ipc.registry import AgentreeRegistry, IPC_DIR
from vibe.core.ipc.terminal.factory import NoTerminalBackendError, detect_backend
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

PID_WAIT_TIMEOUT = 10.0
PID_POLL_INTERVAL = 0.1


class SpawnSessionArgs(BaseModel):
    """Arguments for spawning a new agent session."""

    prompt: str = Field(description="The task/prompt for the new agent session")
    cwd: str = Field(default="", description="Working directory for the new session (empty = current directory)")
    context_files: list[str] = Field(
        default_factory=list,
        description="List of file paths to read and inject as context into the agent's prompt",
    )


class SpawnSessionResult(BaseModel):
    """Result of spawning a new session."""

    pid: int = Field(description="PID of the spawned vibe process")
    session_id: str = Field(description="Unique session identifier")


class SpawnSessionConfig(BaseToolConfig):
    """Config for spawn_session tool."""

    permission: ToolPermission = ToolPermission.ALWAYS


class SpawnSession(
    BaseTool[SpawnSessionArgs, SpawnSessionResult, SpawnSessionConfig, BaseToolState],
    ToolUIData[SpawnSessionArgs, SpawnSessionResult],
):
    """Spawn a new vibe agent session in a separate terminal window."""

    description: ClassVar[str] = (
        "Spawn a new vibe agent session in a separate terminal. "
        "The agent runs autonomously with auto-approve permissions. "
        "Use send_message to communicate with it, read_session to see its output."
    )

    @classmethod
    def is_available(cls) -> bool:
        """Only available when agentree mode is enabled."""
        return agentree_state.is_enabled()

    @classmethod
    def get_call_display(cls, event: ToolCallEvent) -> ToolCallDisplay:
        """Display info for the tool call."""
        args = event.args
        if isinstance(args, SpawnSessionArgs):
            prompt_preview = args.prompt[:60] + "..." if len(args.prompt) > 60 else args.prompt
            return ToolCallDisplay(summary=f"Spawning agent: {prompt_preview}")
        return ToolCallDisplay(summary="Spawning agent")

    @classmethod
    def get_result_display(cls, event: ToolResultEvent) -> ToolResultDisplay:
        """Display info for the tool result."""
        result = event.result
        if isinstance(result, SpawnSessionResult):
            return ToolResultDisplay(success=True, message=f"Agent spawned (pid:{result.pid})")
        return ToolResultDisplay(success=True, message="Agent spawned")

    @classmethod
    def get_status_text(cls) -> str:
        """Status text shown during execution."""
        return "Spawning agent..."

    async def run(
        self, args: SpawnSessionArgs, ctx: InvokeContext | None = None
    ) -> AsyncGenerator[ToolStreamEvent | SpawnSessionResult, None]:
        """Spawn a new vibe session in a terminal."""
        session_id = uuid.uuid4().hex[:12]
        pid_file = IPC_DIR / f"pid_{session_id}"
        cwd = args.cwd or os.getcwd()

        # Build the prompt with context files
        context_files = args.context_files if args.context_files else None
        full_prompt = self._build_prompt(args.prompt, context_files)

        # Build the vibe command
        vibe_bin = sys.argv[0] if sys.argv else "vibe"
        cmd = [
            vibe_bin,
            "--agent", "auto-approve",
            "--ipc-mode",
            "--ipc-parent-pid", str(os.getpid()),
            "--ipc-session-id", session_id,
            "--ipc-pid-file", str(pid_file),
            full_prompt,
        ]

        # Detect terminal backend and spawn
        try:
            from vibe.core.config import VibeConfig

            vibe_config = VibeConfig.load()
            override = vibe_config.agentree.terminal_backend or None
            backend = detect_backend(override=override)
        except NoTerminalBackendError as e:
            raise ToolError(str(e)) from e

        title = f"vibe:{session_id[:8]}"
        try:
            backend.spawn(cmd, title=title, cwd=cwd)
        except Exception as e:
            raise ToolError(f"Failed to spawn terminal: {e}") from e

        # Wait for the child to write its PID
        pid = self._wait_for_pid(pid_file)
        if pid is None:
            raise ToolError("Spawned agent did not start within timeout")

        yield SpawnSessionResult(pid=pid, session_id=session_id)

    def _build_prompt(self, prompt: str, context_files: list[str] | None) -> str:
        """Build the full prompt, optionally prepending file contents."""
        if not context_files:
            return prompt

        context_parts = []
        for path_str in context_files:
            path = Path(path_str).expanduser().resolve()
            if path.is_file():
                try:
                    content = path.read_text(errors="replace")
                    context_parts.append(f"--- {path} ---\n{content}")
                except OSError:
                    context_parts.append(f"--- {path} --- (unreadable)")
            else:
                context_parts.append(f"--- {path} --- (not found)")

        context_block = "\n\n".join(context_parts)
        return f"<context>\n{context_block}\n</context>\n\n{prompt}"

    def _wait_for_pid(self, pid_file: Path) -> int | None:
        """Wait for the child to write its PID to the pid file."""
        start = time.monotonic()
        while time.monotonic() - start < PID_WAIT_TIMEOUT:
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    pid_file.unlink(missing_ok=True)
                    return pid
                except (ValueError, OSError):
                    pass
            time.sleep(PID_POLL_INTERVAL)
        return None

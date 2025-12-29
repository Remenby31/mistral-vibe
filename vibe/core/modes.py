from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import Any


class ModeSafety(StrEnum):
    SAFE = auto()
    NEUTRAL = auto()
    YOLO = auto()


class AgentMode(StrEnum):
    DEFAULT = auto()
    AUTO_APPROVE = auto()
    PLAN = auto()

    @property
    def display_name(self) -> str:
        return MODE_CONFIGS[self].display_name

    @property
    def description(self) -> str:
        return MODE_CONFIGS[self].description

    @property
    def config_overrides(self) -> dict[str, Any]:
        return MODE_CONFIGS[self].config_overrides

    @property
    def auto_approve(self) -> bool:
        return MODE_CONFIGS[self].auto_approve

    @property
    def safety(self) -> ModeSafety:
        return MODE_CONFIGS[self].safety

    @classmethod
    def from_string(cls, value: str) -> AgentMode | None:
        try:
            return cls(value.lower())
        except ValueError:
            return None


@dataclass(frozen=True)
class ModeConfig:
    display_name: str
    description: str
    safety: ModeSafety = ModeSafety.NEUTRAL
    auto_approve: bool = False
    config_overrides: dict[str, Any] = field(default_factory=dict)


PLAN_MODE_TOOLS = ["grep", "read_file", "todo"]

MODE_CONFIGS: dict[AgentMode, ModeConfig] = {
    AgentMode.DEFAULT: ModeConfig(
        display_name="Default",
        description="Requires approval for tool executions",
        safety=ModeSafety.NEUTRAL,
        auto_approve=False,
    ),
    AgentMode.PLAN: ModeConfig(
        display_name="Plan",
        description="Read-only mode for exploration and planning",
        safety=ModeSafety.SAFE,
        auto_approve=True,
        config_overrides={"enabled_tools": PLAN_MODE_TOOLS},
    ),
    AgentMode.AUTO_APPROVE: ModeConfig(
        display_name="Auto Approve",
        description="Auto-approves all tool executions",
        safety=ModeSafety.YOLO,
        auto_approve=True,
    ),
}


def get_mode_order() -> list[AgentMode]:
    return [
        AgentMode.AUTO_APPROVE,
        AgentMode.PLAN,
        AgentMode.DEFAULT,
    ]


def next_mode(current: AgentMode) -> AgentMode:
    order = get_mode_order()
    idx = order.index(current)
    return order[(idx + 1) % len(order)]

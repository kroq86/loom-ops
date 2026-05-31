from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

from loom_ops.state import RunbookState, Message


@dataclass(frozen=True)
class LLMFinish:
    answer: str


@dataclass(frozen=True)
class LLMToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMReply:
    action: Literal["finish", "tool_call"]
    finish: LLMFinish | None = None
    tool_call: LLMToolCall | None = None


class LLMClient(Protocol):
    async def decide(self, state: RunbookState, *, tool_names: list[str]) -> LLMReply: ...


BUDGET_EXCEEDED_MSG = (
    "This run reached the maximum number of tool calls allowed. "
    "Narrow the request or raise LOOM_OPS_MAX_TOOL_CALLS."
)


SYSTEM_PROMPT = """You are an ops runbook assistant. Respond with JSON only:
{"action":"finish","answer":"..."} OR {"action":"tool_call","name":"tool_name","arguments":{...}}
Available tools: {tools}
"""

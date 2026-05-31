from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from loom_ops.state import Message


@dataclass(frozen=True)
class SupervisorState:
    run_id: str
    user_message: str
    messages: tuple[Message, ...]
    tool_calls_used: int
    max_tool_calls: int
    final_answer: str | None
    phase: Literal["think", "done", "awaiting_child"]
    pending_child_run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "user_message": self.user_message,
            "messages": [message.to_dict() for message in self.messages],
            "tool_calls_used": self.tool_calls_used,
            "max_tool_calls": self.max_tool_calls,
            "final_answer": self.final_answer,
            "phase": self.phase,
            "pending_child_run_id": self.pending_child_run_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SupervisorState:
        return cls(
            run_id=str(data["run_id"]),
            user_message=str(data["user_message"]),
            messages=tuple(Message.from_dict(item) for item in data.get("messages", [])),
            tool_calls_used=int(data.get("tool_calls_used", 0)),
            max_tool_calls=int(data.get("max_tool_calls", 10)),
            final_answer=data.get("final_answer"),
            phase=data.get("phase", "think"),
            pending_child_run_id=data.get("pending_child_run_id"),
        )


def encode_state(state: SupervisorState) -> dict[str, Any]:
    return state.to_dict()


def decode_state(data: Any) -> SupervisorState:
    if not isinstance(data, dict):
        raise TypeError("state must be a dict")
    return SupervisorState.from_dict(data)


def encode_result(result: dict[str, Any]) -> dict[str, Any]:
    return dict(result)


def decode_result(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError("result must be a dict")
    return dict(data)

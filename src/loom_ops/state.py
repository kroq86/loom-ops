from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant", "tool"]
    content: str
    tool_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_name is not None:
            data["tool_name"] = self.tool_name
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        return cls(
            role=data["role"],
            content=str(data["content"]),
            tool_name=data.get("tool_name"),
        )


@dataclass(frozen=True)
class RunbookState:
    user_message: str
    messages: tuple[Message, ...]
    tool_calls_used: int
    max_tool_calls: int
    final_answer: str | None
    phase: Literal["think", "done", "awaiting_approval"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_message": self.user_message,
            "messages": [message.to_dict() for message in self.messages],
            "tool_calls_used": self.tool_calls_used,
            "max_tool_calls": self.max_tool_calls,
            "final_answer": self.final_answer,
            "phase": self.phase,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunbookState:
        return cls(
            user_message=str(data["user_message"]),
            messages=tuple(Message.from_dict(item) for item in data.get("messages", [])),
            tool_calls_used=int(data.get("tool_calls_used", 0)),
            max_tool_calls=int(data.get("max_tool_calls", 10)),
            final_answer=data.get("final_answer"),
            phase=data.get("phase", "think"),
        )


def encode_state(state: RunbookState) -> dict[str, Any]:
    return state.to_dict()


def decode_state(data: Any) -> RunbookState:
    if not isinstance(data, dict):
        raise TypeError("state must be a dict")
    return RunbookState.from_dict(data)


def encode_result(result: dict[str, Any]) -> dict[str, Any]:
    return dict(result)


def decode_result(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError("result must be a dict")
    return dict(data)

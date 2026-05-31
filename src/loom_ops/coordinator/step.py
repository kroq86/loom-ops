from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from loom_agent import Complete, Continue, RunContext
from loom_agent.tools import ToolRegistry

from loom_ops.coordinator.llm import BUDGET_EXCEEDED_MSG, LLMClient
from loom_ops.state import Message, RunbookState


StepFn = Callable[[RunbookState, RunContext], Awaitable[Continue[RunbookState] | Complete[dict[str, Any]]]]


def make_step(llm: LLMClient, tools: ToolRegistry) -> StepFn:
    async def step(state: RunbookState, ctx: RunContext) -> Continue[RunbookState] | Complete[dict]:
        if state.phase == "done" and state.final_answer is not None:
            return Complete({"answer": state.final_answer, "tool_calls_used": state.tool_calls_used})

        if state.tool_calls_used >= state.max_tool_calls:
            return Complete(
                {
                    "answer": BUDGET_EXCEEDED_MSG,
                    "tool_calls_used": state.tool_calls_used,
                }
            )

        reply = await llm.decide(state, tool_names=tools.names())

        if reply.action == "finish":
            answer = reply.finish.answer if reply.finish else ""
            done = RunbookState(
                user_message=state.user_message,
                messages=state.messages + (Message(role="assistant", content=answer),),
                tool_calls_used=state.tool_calls_used,
                max_tool_calls=state.max_tool_calls,
                final_answer=answer,
                phase="done",
            )
            return Complete({"answer": answer, "tool_calls_used": state.tool_calls_used})

        tool_call = reply.tool_call
        if tool_call is None:
            return Complete(
                {
                    "answer": "LLM returned tool_call without payload",
                    "tool_calls_used": state.tool_calls_used,
                }
            )

        payload = await ctx.call_tool(tool_call.name, **tool_call.arguments)
        tool_text = _format_tool_payload(payload)
        next_phase: str = "think"
        inner = _tool_payload_dict(payload)
        if tool_call.name == "await_approval" and inner.get("status") == "needs_approval":
            next_phase = "awaiting_approval"

        next_state = RunbookState(
            user_message=state.user_message,
            messages=state.messages
            + (
                Message(role="assistant", content=f"tool:{tool_call.name}"),
                Message(role="tool", content=tool_text, tool_name=tool_call.name),
            ),
            tool_calls_used=state.tool_calls_used + 1,
            max_tool_calls=state.max_tool_calls,
            final_answer=None,
            phase=next_phase,  # type: ignore[arg-type]
        )
        return Continue(next_state)

    return step


def _format_tool_payload(payload: object) -> str:
    inner = _tool_payload_dict(payload)
    if inner:
        return str(inner)[:2000]
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        return str(payload)[:2000]
    return str(payload)[:2000]


def _tool_payload_dict(payload: object) -> dict:
    if hasattr(payload, "payload"):
        inner = getattr(payload, "payload")
        return inner if isinstance(inner, dict) else {}
    if isinstance(payload, dict):
        nested = payload.get("payload")
        if isinstance(nested, dict):
            return nested
        return payload
    return {}

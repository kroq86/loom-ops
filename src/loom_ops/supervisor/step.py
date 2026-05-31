from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from loom_agent import Complete, Continue, RunContext
from loom_agent.tools import ToolRegistry

from loom_ops.coordinator.llm import BUDGET_EXCEEDED_MSG, LLMReply
from loom_ops.coordinator.step import _format_tool_payload, _tool_payload_dict
from loom_ops.state import Message
from loom_ops.supervisor.state import SupervisorState


class SupervisorLLM(Protocol):
    async def decide(self, state: SupervisorState, *, tool_names: list[str]) -> LLMReply: ...


StepFn = Callable[
    [SupervisorState, RunContext],
    Awaitable[Continue[SupervisorState] | Complete[dict[str, Any]]],
]


def make_supervisor_step(llm: SupervisorLLM, tools: ToolRegistry) -> StepFn:
    async def step(state: SupervisorState, ctx: RunContext) -> Continue[SupervisorState] | Complete[dict]:
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
            done = SupervisorState(
                run_id=state.run_id,
                user_message=state.user_message,
                messages=state.messages + (Message(role="assistant", content=answer),),
                tool_calls_used=state.tool_calls_used,
                max_tool_calls=state.max_tool_calls,
                final_answer=answer,
                phase="done",
                pending_child_run_id=None,
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
        inner = _tool_payload_dict(payload)
        next_phase: str = "think"
        pending_child_run_id = state.pending_child_run_id
        if inner.get("status") == "paused":
            next_phase = "awaiting_child"
            pending_child_run_id = str(inner.get("paused_run_id") or inner.get("run_id") or "")

        next_state = SupervisorState(
            run_id=state.run_id,
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
            pending_child_run_id=pending_child_run_id or None,
        )
        return Continue(next_state)

    return step

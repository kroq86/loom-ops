from __future__ import annotations

from loom_ops.coordinator.llm import LLMFinish, LLMReply, LLMToolCall
from loom_ops.supervisor.delegate import PARALLEL_BATCH_ROLES
from loom_ops.supervisor.state import SupervisorState

OPS_ROLES = ("planner", "executor", "verifier")


class MockOpsSupervisorLLM:
    """Ops team: planner → parallel executor+verifier → merge."""

    async def decide(self, state: SupervisorState, *, tool_names: list[str]) -> LLMReply:
        if state.phase == "awaiting_child":
            child_id = state.pending_child_run_id or "unknown"
            return LLMReply(
                action="finish",
                finish=LLMFinish(
                    answer=f"Supervisor paused: child awaiting approval ({child_id})",
                ),
            )

        if "delegate_subagent" not in tool_names and "delegate_subagents_batch" not in tool_names:
            return LLMReply(
                action="finish",
                finish=LLMFinish(answer="Supervisor: no delegate tool available."),
            )

        delegated = _delegated_roles(state)
        if "planner" not in delegated:
            return LLMReply(
                action="tool_call",
                tool_call=LLMToolCall(
                    name="delegate_subagent",
                    arguments={
                        "parent_run_id": state.run_id,
                        "agent_name": "planner",
                        "message": f"planner task: {state.user_message or 'incident response'}",
                    },
                ),
            )

        if not PARALLEL_BATCH_ROLES <= delegated:
            return LLMReply(
                action="tool_call",
                tool_call=LLMToolCall(
                    name="delegate_subagents_batch",
                    arguments={
                        "parent_run_id": state.run_id,
                        "agent_names": sorted(PARALLEL_BATCH_ROLES),
                        "message": f"parallel task: {state.user_message or 'incident response'}",
                    },
                ),
            )

        child_answer = _last_tool_answer(state)
        return LLMReply(
            action="finish",
            finish=LLMFinish(answer=f"Supervisor merged: {child_answer}"),
        )


class OpenAISupervisorLLM:
    """OpenAI-backed supervisor when LOOM_OPS_OPENAI=1."""

    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def decide(self, state: SupervisorState, *, tool_names: list[str]) -> LLMReply:
        from loom_ops.coordinator.llm_impl import OpenAIClient
        from loom_ops.state import RunbookState

        adapter = OpenAIClient(api_key=self._api_key, model=self._model)
        adapted = RunbookState(
            user_message=state.user_message,
            messages=state.messages,
            tool_calls_used=state.tool_calls_used,
            max_tool_calls=state.max_tool_calls,
            final_answer=state.final_answer,
            phase="think" if state.phase == "think" else "done",
        )
        reply = await adapter.decide(adapted, tool_names=tool_names)
        return reply


def create_supervisor_llm(*, mock_llm: bool, openai_api_key: str | None, openai_model: str):
    if mock_llm:
        return MockOpsSupervisorLLM()
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY required when LOOM_OPS_MOCK_LLM=0")
    return OpenAISupervisorLLM(api_key=openai_api_key, model=openai_model)


def _delegated_roles(state: SupervisorState) -> set[str]:
    roles: set[str] = set()
    for message in state.messages:
        if message.role != "tool":
            continue
        content = message.content
        for role in OPS_ROLES:
            if f"'agent_name': '{role}'" in content or f'"agent_name": "{role}"' in content:
                roles.add(role)
        if "'agent_names': ['executor', 'verifier']" in content:
            roles.update(PARALLEL_BATCH_ROLES)
        if '"agent_names": ["executor", "verifier"]' in content:
            roles.update(PARALLEL_BATCH_ROLES)
        if "'agent_names': ['verifier', 'executor']" in content:
            roles.update(PARALLEL_BATCH_ROLES)
    return roles


def _last_tool_answer(state: SupervisorState) -> str:
    tool_msgs = [m for m in state.messages if m.role == "tool"]
    if tool_msgs:
        return tool_msgs[-1].content[:500]
    return "No subagent output."

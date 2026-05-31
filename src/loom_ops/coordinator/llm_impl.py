from __future__ import annotations

import json

from loom_ops.coordinator.llm import LLMClient, LLMFinish, LLMReply, LLMToolCall, SYSTEM_PROMPT
from loom_ops.state import RunbookState


class MockOpsLLM(LLMClient):
    """Role-aware deterministic ops scenario for CI."""

    def __init__(self, *, role: str | None = None) -> None:
        self._role = role or "full"

    async def decide(self, state: RunbookState, *, tool_names: list[str]) -> LLMReply:
        if state.phase == "awaiting_approval":
            if _has_approval_message(state):
                return LLMReply(
                    action="finish",
                    finish=LLMFinish(answer="Approval received; step completed."),
                )
            return LLMReply(
                action="finish",
                finish=LLMFinish(answer="Awaiting human approval."),
            )

        role = self._role
        used = state.tool_calls_used

        if role == "planner":
            if used == 0 and "read_runbook" in tool_names:
                return LLMReply(
                    action="tool_call",
                    tool_call=LLMToolCall(
                        name="read_runbook",
                        arguments={"runbook_name": "incident-response.md"},
                    ),
                )
            return LLMReply(
                action="finish",
                finish=LLMFinish(answer=_summarize(state, "Plan: triage → isolate → rollback → verify → postmortem")),
            )

        if role == "executor":
            if _has_approval_message(state):
                return LLMReply(
                    action="finish",
                    finish=LLMFinish(answer="Approval received; step completed."),
                )
            if used == 0 and "execute_step" in tool_names:
                return LLMReply(
                    action="tool_call",
                    tool_call=LLMToolCall(
                        name="execute_step",
                        arguments={"action": "rollback", "step_id": "rollback"},
                    ),
                )
            if used == 1 and "await_approval" in tool_names:
                return LLMReply(
                    action="tool_call",
                    tool_call=LLMToolCall(
                        name="await_approval",
                        arguments={
                            "step_id": "rollback",
                            "reason": "Destructive rollback requires approval",
                        },
                    ),
                )
            return LLMReply(
                action="finish",
                finish=LLMFinish(answer=_summarize(state, "Executor: rollback staged")),
            )

        if role == "verifier":
            if used == 0 and "check_health" in tool_names:
                return LLMReply(
                    action="tool_call",
                    tool_call=LLMToolCall(
                        name="check_health",
                        arguments={"service": "api"},
                    ),
                )
            if used == 1 and "record_audit" in tool_names:
                return LLMReply(
                    action="tool_call",
                    tool_call=LLMToolCall(
                        name="record_audit",
                        arguments={
                            "event": "incident_closed",
                            "detail": "health ok; runbook complete",
                        },
                    ),
                )
            return LLMReply(
                action="finish",
                finish=LLMFinish(answer=_summarize(state, "Verifier: health ok, audit recorded")),
            )

        # full runbook walk (single-agent)
        sequence = [
            ("read_runbook", {"runbook_name": "incident-response.md"}),
            ("execute_step", {"action": "triage", "step_id": "triage"}),
            ("check_health", {"service": "api"}),
            ("record_audit", {"event": "runbook_complete", "detail": "incident-response"}),
        ]
        if used < len(sequence):
            name, args = sequence[used]
            if name in tool_names:
                return LLMReply(action="tool_call", tool_call=LLMToolCall(name=name, arguments=args))
        return LLMReply(
            action="finish",
            finish=LLMFinish(answer=_summarize(state, "Runbook complete")),
        )


class OpenAIClient(LLMClient):
    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def decide(self, state: RunbookState, *, tool_names: list[str]) -> LLMReply:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("install loom-ops with openai extra: pip install 'loom-ops[openai]'") from exc

        client = AsyncOpenAI(api_key=self._api_key)
        prompt = _build_prompt(state, tool_names)
        response = await client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": state.user_message},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        data = json.loads(raw)
        action = data.get("action")
        if action == "tool_call":
            return LLMReply(
                action="tool_call",
                tool_call=LLMToolCall(
                    name=str(data["name"]),
                    arguments=dict(data.get("arguments", {})),
                ),
            )
        return LLMReply(
            action="finish",
            finish=LLMFinish(answer=str(data.get("answer", ""))),
        )


def create_llm(
    *,
    mock_llm: bool,
    openai_api_key: str | None,
    openai_model: str,
    role: str | None = None,
) -> LLMClient:
    if mock_llm:
        return MockOpsLLM(role=role)
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY required when LOOM_OPS_MOCK_LLM=0")
    return OpenAIClient(api_key=openai_api_key, model=openai_model)


def _summarize(state: RunbookState, prefix: str) -> str:
    tool_msgs = [m for m in state.messages if m.role == "tool"]
    if tool_msgs:
        return f"{prefix}: {tool_msgs[-1].content[:400]}"
    return prefix


def _has_approval_message(state: RunbookState) -> bool:
    return any(m.role == "user" and m.content.upper().startswith("APPROVED:") for m in state.messages)


def _build_prompt(state: RunbookState, tool_names: list[str]) -> str:
    transcript = "\n".join(f"{m.role}: {m.content}" for m in state.messages)
    base = SYSTEM_PROMPT.format(tools=", ".join(tool_names) or "(none)")
    if transcript:
        return f"{base}\nTranscript so far:\n{transcript}"
    return base

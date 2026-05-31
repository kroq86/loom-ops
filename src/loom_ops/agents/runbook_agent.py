from __future__ import annotations

from typing import Any

from loom_agent import AgentRunner, SQLiteCheckpointStore

from loom_ops.config import Settings, load_settings
from loom_ops.memory_context import memory_prefix_messages
from loom_ops.coordinator.llm_impl import create_llm
from loom_ops.coordinator.step import make_step
from loom_ops.state import (
    RunbookState,
    Message,
    decode_result,
    decode_state,
    encode_result,
    encode_state,
)
from loom_ops.tools.build_registry import build_tool_registry


def make_initial_state(
    user_message: str,
    *,
    max_tool_calls: int | None = None,
    settings: Settings | None = None,
) -> RunbookState:
    settings = settings or load_settings()
    limit = max_tool_calls if max_tool_calls is not None else settings.max_tool_calls
    prefix = memory_prefix_messages(settings)
    user_messages = (Message(role="user", content=user_message),) if user_message else ()
    messages = prefix + user_messages
    return RunbookState(
        user_message=user_message,
        messages=messages,
        tool_calls_used=0,
        max_tool_calls=limit,
        final_answer=None,
        phase="think",
    )


def build_runner_with_settings(
    db_path: str,
    settings: Settings,
    *,
    role: str | None = None,
    registry=None,
) -> AgentRunner[RunbookState, dict[str, Any]]:
    reg = registry or build_tool_registry(settings, role=role)
    llm = create_llm(
        mock_llm=settings.mock_llm,
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
        role=role,
    )
    step = make_step(llm, reg)
    return AgentRunner(
        step=step,
        store=SQLiteCheckpointStore(db_path),
        encode_state=encode_state,
        decode_state=decode_state,
        encode_result=encode_result,
        decode_result=decode_result,
        tools=reg,
    )


def build_role_runner(
    db_path: str,
    settings: Settings,
    *,
    role: str,
    child_max_steps: int = 20,
) -> AgentRunner[RunbookState, dict[str, Any]]:
    del child_max_steps
    return build_runner_with_settings(db_path, settings, role=role)

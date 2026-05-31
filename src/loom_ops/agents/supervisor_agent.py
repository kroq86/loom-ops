from __future__ import annotations

from typing import Any

from loom_agent import AgentRunner, SQLiteCheckpointStore
from loom_agent.tools import ToolRegistry

from loom_ops.config import Settings, load_settings
from loom_ops.memory_context import memory_prefix_messages
from loom_ops.state import Message
from loom_ops.supervisor.delegate import make_delegate_tools
from loom_ops.supervisor.llm_impl import create_supervisor_llm
from loom_ops.supervisor.state import (
    SupervisorState,
    decode_result,
    decode_state,
    encode_result,
    encode_state,
)
from loom_ops.supervisor.step import make_supervisor_step


def make_supervisor_initial_state(
    run_id: str,
    user_message: str,
    *,
    max_tool_calls: int | None = None,
    settings: Settings | None = None,
) -> SupervisorState:
    settings = settings or load_settings()
    limit = max_tool_calls if max_tool_calls is not None else settings.max_tool_calls
    prefix = memory_prefix_messages(settings)
    user_messages = (Message(role="user", content=user_message),) if user_message else ()
    messages = prefix + user_messages
    return SupervisorState(
        run_id=run_id,
        user_message=user_message,
        messages=messages,
        tool_calls_used=0,
        max_tool_calls=limit,
        final_answer=None,
        phase="think",
        pending_child_run_id=None,
    )


def build_supervisor_runner(
    db_path: str,
    settings: Settings,
    *,
    child_max_steps: int = 20,
) -> AgentRunner[SupervisorState, dict[str, Any]]:
    registry = ToolRegistry()
    delegate_subagent, delegate_batch = make_delegate_tools(
        db_path,
        settings,
        child_max_steps=child_max_steps,
    )
    registry.register("delegate_subagent", delegate_subagent)
    registry.register("delegate_subagents_batch", delegate_batch)
    llm = create_supervisor_llm(
        mock_llm=settings.mock_llm,
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
    )
    step = make_supervisor_step(llm, registry)
    return AgentRunner(
        step=step,
        store=SQLiteCheckpointStore(db_path),
        encode_state=encode_state,
        decode_state=decode_state,
        encode_result=encode_result,
        decode_result=decode_result,
        tools=registry,
    )

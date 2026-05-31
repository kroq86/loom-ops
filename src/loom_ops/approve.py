from __future__ import annotations

import json
from typing import Any

from loom_agent import AgentRunner

from loom_ops.agents.runbook_agent import build_runner_with_settings
from loom_ops.config import Settings
from loom_ops.state import Message, RunbookState, encode_state


def run_needs_approval(runner: AgentRunner[Any, Any], run_id: str) -> bool:
    run = runner.get_run(run_id)
    if run is None or run.state is None:
        return False
    state = run.state
    if isinstance(state, RunbookState):
        return state.phase == "awaiting_approval"
    return False


def _update_paused_state(
    runner: AgentRunner[Any, Any],
    *,
    run_id: str,
    state: RunbookState,
) -> None:
    run = runner.get_run(run_id)
    if run is None:
        raise ValueError(f"run not found: {run_id}")
    state_json = json.dumps(encode_state(state))
    store = runner.store
    with store._connect() as conn:  # noqa: SLF001
        conn.execute(
            """
            update runs
            set state_json = ?,
                status = 'running',
                updated_at = datetime('now')
            where run_id = ?
            """,
            (state_json, run_id),
        )
        conn.execute(
            """
            update steps
            set state_json = ?
            where run_id = ? and step_index = ?
            """,
            (state_json, run_id, run.step_index),
        )
        conn.commit()


async def inject_approval_and_resume(
    db_path: str,
    settings: Settings,
    *,
    run_id: str,
    note: str,
    max_steps: int = 20,
    role: str | None = None,
) -> Any:
    resolved_role = role or _role_from_run_id(run_id)
    runner = build_runner_with_settings(db_path, settings, role=resolved_role)
    run = runner.get_run(run_id)
    if run is None or run.state is None:
        raise ValueError(f"run not found: {run_id}")

    state: RunbookState = run.state
    if state.phase != "awaiting_approval":
        raise ValueError(f"run {run_id} is not awaiting approval (phase={state.phase})")

    approval = Message(role="user", content=f"APPROVED: {note}")
    updated = RunbookState(
        user_message=state.user_message,
        messages=state.messages + (approval,),
        tool_calls_used=state.tool_calls_used,
        max_tool_calls=state.max_tool_calls,
        final_answer=None,
        phase="think",
    )
    _update_paused_state(runner, run_id=run_id, state=updated)

    result = await runner.resume(run_id=run_id, max_steps=1)
    remaining = max_steps - 1
    while result.status == "paused" and remaining > 0:
        result = await runner.resume(run_id=run_id, max_steps=1)
        remaining -= 1
    return result


def _role_from_run_id(run_id: str) -> str | None:
    if ":sub:" not in run_id:
        return None
    return run_id.rsplit(":sub:", 1)[-1]

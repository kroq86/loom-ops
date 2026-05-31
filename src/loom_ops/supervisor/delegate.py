from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from loom_ops.agents.runbook_agent import build_role_runner, make_initial_state
from loom_ops.config import Settings

ToolFn = Callable[..., Awaitable[dict[str, Any]]]

DEFAULT_CHILD_MAX_STEPS = 20
PARALLEL_BATCH_ROLES = frozenset({"executor", "verifier"})


async def run_child_until_settled(
    db_path: str,
    settings: Settings,
    *,
    parent_run_id: str,
    agent_name: str,
    message: str,
    child_max_steps: int = DEFAULT_CHILD_MAX_STEPS,
) -> dict[str, Any]:
    child_run_id = f"{parent_run_id}:sub:{agent_name}"
    runner = build_role_runner(db_path, settings, role=agent_name)
    state = make_initial_state(message, max_tool_calls=settings.max_tool_calls)
    result = await runner.start(
        run_id=child_run_id,
        initial_state=state,
        max_steps=1,
    )
    remaining = child_max_steps - 1
    while result.status == "paused" and remaining > 0:
        result = await runner.resume(run_id=child_run_id, max_steps=1)
        remaining -= 1

    if result.status == "completed" and result.result is not None:
        answer = str(result.result.get("answer", ""))
        return {
            "success": True,
            "result_type": "subagent_delegate",
            "payload": {
                "run_id": child_run_id,
                "agent_name": agent_name,
                "status": result.status,
                "answer": answer,
            },
        }

    return {
        "success": False,
        "is_error": True,
        "result_type": "subagent_delegate",
        "payload": {
            "run_id": child_run_id,
            "agent_name": agent_name,
            "status": result.status,
            "answer": None,
            "needs_approval": result.status == "paused",
        },
    }


async def run_children_parallel(
    db_path: str,
    settings: Settings,
    *,
    parent_run_id: str,
    agent_names: list[str],
    message: str,
    child_max_steps: int = DEFAULT_CHILD_MAX_STEPS,
) -> dict[str, Any]:
    results = await asyncio.gather(
        *[
            run_child_until_settled(
                db_path,
                settings,
                parent_run_id=parent_run_id,
                agent_name=name,
                message=message,
                child_max_steps=child_max_steps,
            )
            for name in agent_names
        ]
    )

    paused = [r for r in results if r.get("payload", {}).get("status") == "paused"]
    if paused:
        first = paused[0]["payload"]
        return {
            "success": True,
            "result_type": "subagent_delegate_batch",
            "payload": {
                "agent_names": agent_names,
                "status": "paused",
                "paused_run_id": first.get("run_id"),
                "paused_agent": first.get("agent_name"),
                "results": results,
            },
        }

    failed = [r for r in results if not r.get("success")]
    if failed:
        return {
            "success": False,
            "is_error": True,
            "result_type": "subagent_delegate_batch",
            "payload": {
                "agent_names": agent_names,
                "status": "error",
                "results": results,
            },
        }

    answers = [r["payload"].get("answer", "") for r in results if r.get("success")]
    return {
        "success": True,
        "result_type": "subagent_delegate_batch",
        "payload": {
            "agent_names": agent_names,
            "status": "completed",
            "answers": answers,
            "results": results,
        },
    }


def make_delegate_tools(
    db_path: str,
    settings: Settings,
    *,
    child_max_steps: int = DEFAULT_CHILD_MAX_STEPS,
) -> tuple[ToolFn, ToolFn]:
    async def delegate_subagent(
        *,
        parent_run_id: str,
        agent_name: str,
        message: str,
    ) -> dict[str, Any]:
        return await run_child_until_settled(
            db_path,
            settings,
            parent_run_id=parent_run_id,
            agent_name=agent_name,
            message=message,
            child_max_steps=child_max_steps,
        )

    async def delegate_subagents_batch(
        *,
        parent_run_id: str,
        agent_names: list[str],
        message: str,
    ) -> dict[str, Any]:
        return await run_children_parallel(
            db_path,
            settings,
            parent_run_id=parent_run_id,
            agent_names=agent_names,
            message=message,
            child_max_steps=child_max_steps,
        )

    return delegate_subagent, delegate_subagents_batch


def make_delegate_tool(
    db_path: str,
    settings: Settings,
    *,
    child_max_steps: int = DEFAULT_CHILD_MAX_STEPS,
) -> ToolFn:
    delegate_subagent, _ = make_delegate_tools(db_path, settings, child_max_steps=child_max_steps)
    return delegate_subagent

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from loom_ops.agents.runbook_agent import build_role_runner, make_initial_state
from loom_ops.agents.supervisor_agent import (
    build_supervisor_runner,
    make_supervisor_initial_state,
)
from loom_ops.approve import inject_approval_and_resume
from loom_ops.config import Settings
from tests.conftest import make_test_settings


@pytest.fixture
def ops_settings(ops_workspace: Path) -> Settings:
    return make_test_settings(ops_workspace)


@pytest.mark.asyncio
async def test_supervisor_delegates_three_roles(ops_settings: Settings) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "ops.sqlite")
        runner = build_supervisor_runner(db, ops_settings)
        state = make_supervisor_initial_state("inc-001", "incident: API latency spike")
        result = await runner.start(run_id="inc-001", initial_state=state, max_steps=20)

        assert result.status == "completed"
        assert result.result is not None
        assert "Supervisor merged" in result.result["answer"]

        explained = runner.explain_run("inc-001")
        assert explained.tool_call_count >= 2

        for role in ("planner", "executor", "verifier"):
            child_id = f"inc-001:sub:{role}"
            child_runner = build_role_runner(db, ops_settings, role=role)
            explained = child_runner.explain_run(child_id)
            assert explained.status == "completed"
            assert explained.tool_call_count >= 1


@pytest.mark.asyncio
async def test_planner_reads_runbook(ops_settings: Settings) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "ops.sqlite")
        runner = build_role_runner(db, ops_settings, role="planner")
        state = make_initial_state("plan incident", max_tool_calls=5)
        result = await runner.start(run_id="plan-1", initial_state=state, max_steps=10)
        assert result.status == "completed"
        assert "Plan:" in result.result["answer"]


@pytest.mark.asyncio
async def test_executor_hitl_approve(ops_settings: Settings) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "ops.sqlite")
        runner = build_role_runner(db, ops_settings, role="executor")
        state = make_initial_state("execute rollback", max_tool_calls=5)
        paused = await runner.start(run_id="exec-1", initial_state=state, max_steps=2)
        assert paused.status == "paused"
        assert paused.state.phase == "awaiting_approval"

        approved = await inject_approval_and_resume(
            db,
            ops_settings,
            run_id="exec-1",
            note="LGTM",
            max_steps=10,
            role="executor",
        )
        assert approved.status == "completed"
        assert "Approval received" in approved.result["answer"]


@pytest.mark.asyncio
async def test_delegate_batch_paused_when_executor_hitl(ops_settings: Settings) -> None:
    from loom_ops.supervisor.delegate import run_children_parallel

    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "ops.sqlite")
        result = await run_children_parallel(
            db,
            ops_settings,
            parent_run_id="inc-hitl",
            agent_names=["executor", "verifier"],
            message="execute rollback",
            child_max_steps=2,
        )
        assert result["success"] is True
        assert result["payload"]["status"] == "paused"
        assert result["payload"]["paused_agent"] == "executor"


@pytest.mark.asyncio
async def test_supervisor_pauses_when_child_needs_approval(ops_settings: Settings) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "ops.sqlite")
        runner = build_supervisor_runner(db, ops_settings, child_max_steps=2)
        state = make_supervisor_initial_state("inc-pause", "incident: API latency spike")
        paused = await runner.start(run_id="inc-pause", initial_state=state, max_steps=2)
        assert paused.status == "paused"
        assert paused.state.phase == "awaiting_child"
        assert paused.state.pending_child_run_id == "inc-pause:sub:executor"

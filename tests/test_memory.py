from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from loom_ops.agents.runbook_agent import build_role_runner, make_initial_state
from loom_ops.memory import MemoryStore
from loom_ops.tools.build_registry import build_tool_registry
from tests.conftest import make_test_settings


@pytest.mark.asyncio
async def test_memory_append_and_inject(ops_workspace: Path) -> None:
    settings = make_test_settings(ops_workspace, memory_enabled=True)
    store = MemoryStore.for_workspace(ops_workspace)
    store.append({"kind": "audit", "summary": "rollback approved"})

    state = make_initial_state("plan incident", max_tool_calls=5, settings=settings)
    assert any("Prior ops context" in m.content for m in state.messages)
    assert any("rollback approved" in m.content for m in state.messages)


@pytest.mark.asyncio
async def test_record_audit_writes_memory(ops_workspace: Path) -> None:
    settings = make_test_settings(ops_workspace, memory_enabled=True)
    registry = build_tool_registry(settings, role="verifier")
    await registry.call_result("record_audit", event="verify", detail="ok")

    entries = MemoryStore.for_workspace(ops_workspace).recent()
    assert entries[-1]["summary"] == "verify ok"


@pytest.mark.asyncio
async def test_child_run_sees_prior_audit(ops_workspace: Path) -> None:
    settings = make_test_settings(ops_workspace, memory_enabled=True)
    registry = build_tool_registry(settings, role="verifier")
    await registry.call_result("record_audit", event="triage", detail="sev2")

    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "ops.sqlite")
        runner = build_role_runner(db, settings, role="planner")
        state = make_initial_state("plan incident", max_tool_calls=5, settings=settings)
        assert any("triage sev2" in m.content for m in state.messages)

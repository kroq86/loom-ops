from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from loom_ops.tools.local import read_runbook_sync
from tests.conftest import make_test_settings


def test_read_runbook(ops_workspace: Path) -> None:
    result = read_runbook_sync(ops_workspace, "incident-response.md")
    assert result["success"] is True
    assert "Incident Response" in result["payload"]["content"]


@pytest.mark.asyncio
async def test_read_runbook_tool_via_registry(ops_workspace: Path) -> None:
    from loom_ops.tools.build_registry import build_tool_registry

    settings = make_test_settings(ops_workspace, user_message="")
    registry = build_tool_registry(settings, role="planner")
    result = await registry.call_result("read_runbook", runbook_name="incident-response.md")
    assert result.success is True
    assert "Triage" in result.payload["content"]


@pytest.mark.asyncio
async def test_execute_step_mock(ops_workspace: Path) -> None:
    from loom_ops.tools.build_registry import build_tool_registry

    settings = make_test_settings(ops_workspace, user_message="")
    registry = build_tool_registry(settings, role="executor")
    result = await registry.call_result("execute_step", action="rollback", step_id="rollback")
    assert result.success is True
    assert result.payload["status"] == "mock_executed"


@pytest.mark.asyncio
async def test_await_approval_payload(ops_workspace: Path) -> None:
    from loom_ops.tools.build_registry import build_tool_registry

    settings = make_test_settings(ops_workspace, user_message="")
    registry = build_tool_registry(settings, role="executor")
    result = await registry.call_result(
        "await_approval",
        step_id="rollback",
        reason="destructive",
    )
    assert result.payload["status"] == "needs_approval"

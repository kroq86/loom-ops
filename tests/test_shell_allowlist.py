from __future__ import annotations

import json
from pathlib import Path

import pytest

from loom_ops.config import Settings
from loom_ops.tools.build_registry import build_tool_registry
from tests.conftest import make_test_settings


@pytest.mark.asyncio
async def test_execute_step_mock_when_shell_disabled(ops_workspace: Path) -> None:
    settings = make_test_settings(ops_workspace, allow_shell=False)
    registry = build_tool_registry(settings, role="executor")
    result = await registry.call_result("execute_step", action="echo ok", step_id="s1")
    assert result.success is True
    assert result.payload["status"] == "mock_executed"


@pytest.mark.asyncio
async def test_execute_step_echo_allowed(ops_workspace: Path) -> None:
    allowlist = ops_workspace / "ops.shell.allowlist.json"
    allowlist.write_text(json.dumps({"commands": [["echo"]]}), encoding="utf-8")
    settings = make_test_settings(
        ops_workspace,
        allow_shell=True,
        shell_allowlist_path=allowlist,
    )
    registry = build_tool_registry(settings, role="executor")
    result = await registry.call_result("execute_step", action="echo loom-ops-test", step_id="s1")
    assert result.success is True
    assert "loom-ops-test" in result.payload["stdout"]


@pytest.mark.asyncio
async def test_execute_step_denied_not_in_allowlist(ops_workspace: Path) -> None:
    allowlist = ops_workspace / "ops.shell.allowlist.json"
    allowlist.write_text(json.dumps({"commands": [["echo"]]}), encoding="utf-8")
    settings = make_test_settings(
        ops_workspace,
        allow_shell=True,
        shell_allowlist_path=allowlist,
    )
    registry = build_tool_registry(settings, role="executor")
    result = await registry.call_result("execute_step", action="rm -rf /", step_id="s1")
    assert result.success is False
    assert "allowlist" in result.payload["error"]


@pytest.mark.asyncio
async def test_is_command_allowed_prefix_match() -> None:
    from loom_ops.tools.shell import is_command_allowed

    allowlist = [["python", "-c"], ["echo"]]
    assert is_command_allowed(["echo", "hi"], allowlist)
    assert is_command_allowed(["python", "-c", "print(1)"], allowlist)
    assert not is_command_allowed(["python", "script.py"], allowlist)

from __future__ import annotations

from pathlib import Path

import pytest

from loom_ops.config import Settings


def make_test_settings(workspace: Path, **overrides: object) -> Settings:
    defaults = {
        "workspace": workspace,
        "mock_llm": True,
        "openai_api_key": None,
        "openai_model": "gpt-4o-mini",
        "max_tool_calls": 10,
        "user_message": "incident: API latency spike",
        "mcp_config_path": None,
        "allow_shell": False,
        "shell_allowlist_path": None,
        "shell_timeout_sec": 30,
        "memory_enabled": False,
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def ops_workspace(tmp_path: Path) -> Path:
    runbooks = tmp_path / "runbooks"
    runbooks.mkdir()
    (runbooks / "incident-response.md").write_text(
        "# Incident Response\n\n1. Triage\n2. Rollback\n",
        encoding="utf-8",
    )
    return tmp_path

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    workspace: Path
    mock_llm: bool
    openai_api_key: str | None
    openai_model: str
    max_tool_calls: int
    user_message: str
    mcp_config_path: Path | None
    allow_shell: bool
    shell_allowlist_path: Path | None
    shell_timeout_sec: int
    memory_enabled: bool


def load_settings() -> Settings:
    mock_raw = os.environ.get("LOOM_OPS_MOCK_LLM", "1").strip().lower()
    mock_llm = mock_raw in {"1", "true", "yes", "on"}
    api_key = os.environ.get("OPENAI_API_KEY") or None
    if api_key and os.environ.get("LOOM_OPS_OPENAI", "").strip().lower() in {"1", "true", "yes", "on"}:
        mock_llm = False
    elif api_key and os.environ.get("LOOM_OPS_MOCK_LLM", "1").strip().lower() not in {"1", "true", "yes", "on"}:
        mock_llm = False

    workspace = Path(os.environ.get("LOOM_OPS_WORKSPACE", os.getcwd())).resolve()
    mcp_path = os.environ.get("LOOM_OPS_MCP_CONFIG")
    allow_shell = os.environ.get("LOOM_OPS_ALLOW_SHELL", "").strip().lower() in {"1", "true", "yes", "on"}
    shell_allowlist_env = os.environ.get("LOOM_OPS_SHELL_ALLOWLIST", "").strip()
    shell_allowlist_path = Path(shell_allowlist_env).resolve() if shell_allowlist_env else None
    shell_timeout_sec = max(1, int(os.environ.get("LOOM_OPS_SHELL_TIMEOUT_SEC", "30")))
    memory_enabled = os.environ.get("LOOM_OPS_MEMORY", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return Settings(
        workspace=workspace,
        mock_llm=mock_llm,
        openai_api_key=api_key,
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        max_tool_calls=max(1, int(os.environ.get("LOOM_OPS_MAX_TOOL_CALLS", "10"))),
        user_message=os.environ.get("LOOM_OPS_USER_MESSAGE", ""),
        mcp_config_path=Path(mcp_path).resolve() if mcp_path else None,
        allow_shell=allow_shell,
        shell_allowlist_path=shell_allowlist_path,
        shell_timeout_sec=shell_timeout_sec,
        memory_enabled=memory_enabled,
    )

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

_SENSITIVE_ENV_PREFIXES = (
    "OPENAI_",
    "TELEGRAM_",
    "AWS_",
    "PYPI_",
    "GITHUB_",
    "GH_",
    "TWINE_",
)


def _child_process_env(config_env: dict[str, str]) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(_SENSITIVE_ENV_PREFIXES)
    }
    env.update(config_env)
    return env


@dataclass
class McpServerConfig:
    command: str
    args: list[str]
    env: dict[str, str]
    tool_map: dict[str, str]


class McpStdioClient:
    def __init__(self, config: McpServerConfig) -> None:
        self._config = config
        self._proc: Any = None
        self._reader: Any = None
        self._writer: Any = None
        self._lock: Any = None
        self._next_id = 1
        self._initialized = False

    async def start(self) -> None:
        import asyncio

        if self._proc is not None:
            return
        if self._lock is None:
            self._lock = asyncio.Lock()
        env = _child_process_env(self._config.env)
        self._proc = await asyncio.create_subprocess_exec(
            self._config.command,
            *self._config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        assert self._proc.stdout is not None
        assert self._proc.stdin is not None
        self._reader = self._proc.stdout
        self._writer = self._proc.stdin
        await self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "loom-ops", "version": "0.2.1"},
            },
        )
        await self._notify("notifications/initialized", {})
        self._initialized = True

    async def call_tool(self, mcp_tool_name: str, arguments: dict[str, Any]) -> Any:
        await self.start()
        result = await self._request(
            "tools/call",
            {"name": mcp_tool_name, "arguments": arguments},
        )
        return _extract_tool_content(result)

    async def close(self) -> None:
        if self._proc is None:
            return
        if self._proc.stdin:
            self._proc.stdin.close()
        await self._proc.wait()
        self._proc = None
        self._reader = None
        self._writer = None
        self._initialized = False

    async def _request(self, method: str, params: dict[str, Any]) -> Any:
        import asyncio

        async with self._lock:
            assert self._writer is not None
            assert self._reader is not None
            req_id = self._next_id
            self._next_id += 1
            payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
            self._writer.write((json.dumps(payload) + "\n").encode())
            await self._writer.drain()
            while True:
                line = await self._reader.readline()
                if not line:
                    raise RuntimeError("MCP server closed stdout")
                message = json.loads(line.decode())
                if message.get("id") != req_id:
                    continue
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message.get("result")

    async def _notify(self, method: str, params: dict[str, Any]) -> None:
        async with self._lock:
            assert self._writer is not None
            payload = {"jsonrpc": "2.0", "method": method, "params": params}
            self._writer.write((json.dumps(payload) + "\n").encode())
            await self._writer.drain()


def _extract_tool_content(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    content = result.get("content")
    if not isinstance(content, list):
        return result
    texts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            texts.append(str(item.get("text", "")))
    if len(texts) == 1:
        try:
            return json.loads(texts[0])
        except json.JSONDecodeError:
            return texts[0]
    return {"texts": texts}


def load_mcp_config(path: str) -> dict[str, McpServerConfig]:
    raw = json.loads(open(path, encoding="utf-8").read())
    configs: dict[str, McpServerConfig] = {}
    for name, entry in raw.items():
        configs[name] = McpServerConfig(
            command=str(entry["command"]),
            args=[str(arg) for arg in entry.get("args", [])],
            env={str(k): str(v) for k, v in entry.get("env", {}).items()},
            tool_map={str(k): str(v) for k, v in entry.get("tools", {}).items()},
        )
    return configs

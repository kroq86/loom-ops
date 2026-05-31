from __future__ import annotations

import asyncio
import json
import shlex
from pathlib import Path
from typing import Any

MAX_OUTPUT_BYTES = 8192
DEFAULT_TIMEOUT_SEC = 30


def load_allowlist(path: Path) -> list[list[str]]:
    if not path.is_file():
        raise FileNotFoundError(f"shell allowlist not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    commands = data.get("commands")
    if not isinstance(commands, list):
        raise ValueError("allowlist must contain a 'commands' array")
    parsed: list[list[str]] = []
    for entry in commands:
        if not isinstance(entry, list) or not entry:
            raise ValueError("each allowlist entry must be a non-empty command prefix list")
        parsed.append([str(part) for part in entry])
    return parsed


def resolve_allowlist_path(workspace: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return (workspace / "ops.shell.allowlist.json").resolve()


def is_command_allowed(argv: list[str], allowlist: list[list[str]]) -> bool:
    if not argv:
        return False
    for prefix in allowlist:
        if len(argv) < len(prefix):
            continue
        if argv[: len(prefix)] == prefix:
            return True
    return False


def _truncate(text: str, limit: int = MAX_OUTPUT_BYTES) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... [truncated]"


async def run_allowed_shell(
    action: str,
    *,
    allowlist: list[list[str]],
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    cwd: Path | None = None,
) -> dict[str, Any]:
    try:
        argv = shlex.split(action)
    except ValueError as exc:
        return _error_payload(action, f"invalid shell action: {exc}")

    if not is_command_allowed(argv, allowlist):
        return _error_payload(action, "command not in shell allowlist")

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd) if cwd else None,
        )
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout_sec,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return _error_payload(action, f"command timed out after {timeout_sec}s")
    except OSError as exc:
        return _error_payload(action, f"failed to execute: {exc}")

    stdout = _truncate(stdout_b.decode(errors="replace"))
    stderr = _truncate(stderr_b.decode(errors="replace"))
    exit_code = proc.returncode if proc.returncode is not None else -1
    return {
        "success": exit_code == 0,
        "is_error": exit_code != 0,
        "result_type": "execute_step",
        "payload": {
            "action": action,
            "argv": argv,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "status": "executed" if exit_code == 0 else "failed",
        },
    }


def _error_payload(action: str, error: str) -> dict[str, Any]:
    return {
        "success": False,
        "is_error": True,
        "result_type": "execute_step",
        "payload": {"action": action, "error": error},
    }

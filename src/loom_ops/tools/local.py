from __future__ import annotations

import json
from pathlib import Path

from loom_agent.tools import ToolRegistry

from loom_ops.config import Settings
from loom_ops.memory import MemoryStore
from loom_ops.tools.shell import (
    load_allowlist,
    resolve_allowlist_path,
    run_allowed_shell,
)

ROLE_TOOLS: dict[str, tuple[str, ...]] = {
    "planner": ("read_runbook",),
    "executor": ("execute_step", "await_approval"),
    "verifier": ("check_health", "record_audit"),
}

ALL_OPS_TOOLS = ("read_runbook", "execute_step", "check_health", "record_audit", "await_approval")


def register_ops_tools(
    registry: ToolRegistry,
    settings: Settings,
    *,
    role: str | None = None,
    skip_tools: set[str] | None = None,
) -> None:
    workspace = settings.workspace
    audit_log: list[dict[str, str]] = []

    async def read_runbook(runbook_name: str = "incident-response.md") -> dict:
        target = _resolve_runbook_path(workspace, runbook_name)
        text = target.read_text(encoding="utf-8")
        if settings.memory_enabled:
            MemoryStore.for_workspace(workspace).append(
                {
                    "kind": "runbook",
                    "summary": f"{runbook_name}: {text[:200].replace(chr(10), ' ')}",
                }
            )
        return {
            "success": True,
            "result_type": "runbook_read",
            "payload": {"name": runbook_name, "content": text[:8000]},
        }

    async def execute_step(action: str, *, step_id: str = "step") -> dict:
        if settings.allow_shell:
            allowlist_path = resolve_allowlist_path(
                workspace,
                settings.shell_allowlist_path,
            )
            allowlist = load_allowlist(allowlist_path)
            result = await run_allowed_shell(
                action,
                allowlist=allowlist,
                timeout_sec=settings.shell_timeout_sec,
                cwd=workspace,
            )
            payload = dict(result.get("payload", {}))
            payload["step_id"] = step_id
            return {**result, "payload": payload}
        return {
            "success": True,
            "result_type": "execute_step",
            "payload": {
                "step_id": step_id,
                "action": action,
                "status": "mock_executed",
                "message": f"Mock executed: {action}",
            },
        }

    async def check_health(service: str = "api") -> dict:
        return {
            "success": True,
            "result_type": "health_check",
            "payload": {"service": service, "status": "ok", "latency_ms": 42},
        }

    async def record_audit(event: str, *, detail: str = "") -> dict:
        entry = {"event": event, "detail": detail}
        audit_log.append(entry)
        if settings.memory_enabled:
            MemoryStore.for_workspace(workspace).append(
                {
                    "kind": "audit",
                    "summary": f"{event} {detail}".strip(),
                }
            )
        return {
            "success": True,
            "result_type": "audit_record",
            "payload": {"entry": entry, "total_entries": len(audit_log)},
        }

    async def await_approval(step_id: str, reason: str) -> dict:
        return {
            "success": True,
            "result_type": "approval_request",
            "payload": {
                "status": "needs_approval",
                "step_id": step_id,
                "reason": reason,
            },
        }

    tool_fns = {
        "read_runbook": read_runbook,
        "execute_step": execute_step,
        "check_health": check_health,
        "record_audit": record_audit,
        "await_approval": await_approval,
    }

    allowed = ROLE_TOOLS.get(role, ALL_OPS_TOOLS) if role else ALL_OPS_TOOLS
    skipped = skip_tools or set()
    for name in allowed:
        if name in skipped:
            continue
        registry.register(name, tool_fns[name])


def _resolve_runbook_path(workspace: Path, name: str) -> Path:
    if name.startswith("/") or ".." in Path(name).parts:
        raise PermissionError(f"invalid runbook path: {name}")
    candidate = (workspace / "runbooks" / name).resolve()
    runbooks_root = (workspace / "runbooks").resolve()
    if runbooks_root not in candidate.parents and candidate != runbooks_root:
        raise PermissionError(f"path escapes runbooks/: {name}")
    if not candidate.is_file():
        raise FileNotFoundError(name)
    return candidate


def read_runbook_sync(workspace: Path, name: str = "incident-response.md") -> dict:
    target = _resolve_runbook_path(workspace, name)
    text = target.read_text(encoding="utf-8")
    return {
        "success": True,
        "result_type": "runbook_read",
        "payload": {"name": name, "content": text},
    }

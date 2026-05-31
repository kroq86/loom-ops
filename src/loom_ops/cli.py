from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from flow_xray import trace

from loom_ops.agents.runbook_agent import build_runner_with_settings, make_initial_state
from loom_ops.agents.supervisor_agent import (
    build_supervisor_runner,
    make_supervisor_initial_state,
)
from loom_ops.approve import inject_approval_and_resume
from loom_ops.config import Settings, load_settings


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "serve":
        return _run_serve(args)
    if args.command == "telegram":
        return _run_telegram(args)
    settings = _settings_from_args(args)

    if args.command == "supervise":
        runner = build_supervisor_runner(args.db, settings, child_max_steps=args.max_steps)
    else:
        runner = build_runner_with_settings(args.db, settings)

    async def execute() -> Any:
        if args.command == "runbook":
            state = make_initial_state(args.message, max_tool_calls=args.max_tool_calls)
            runbook_runner = build_runner_with_settings(args.db, settings)
            return await runbook_runner.start(
                run_id=args.run_id,
                initial_state=state,
                max_steps=args.max_steps,
            )
        if args.command == "supervise":
            state = make_supervisor_initial_state(
                args.run_id,
                args.message,
                max_tool_calls=args.max_tool_calls,
            )
            return await runner.start(
                run_id=args.run_id,
                initial_state=state,
                max_steps=args.max_steps,
            )
        if args.command == "resume":
            return await runner.resume(run_id=args.run_id, max_steps=args.max_steps)
        if args.command == "explain":
            return runner.explain_run(args.run_id)
        if args.command == "approve":
            return await inject_approval_and_resume(
                args.db,
                settings,
                run_id=args.run_id,
                note=args.note,
                max_steps=args.max_steps,
                role=getattr(args, "role", None),
            )
        raise ValueError(f"unknown command: {args.command}")

    if getattr(args, "trace", None):
        result = trace.run(lambda: asyncio.run(execute()))
        result.to_html(args.trace)
        payload = result.return_value
    else:
        payload = asyncio.run(execute())

    print(json.dumps(_to_jsonable(payload), sort_keys=True, default=str))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="loom-ops")
    sub = parser.add_subparsers(dest="command", required=True)

    runbook = sub.add_parser("runbook", help="Start a single durable runbook run")
    _add_common_args(runbook)
    runbook.add_argument("message")
    runbook.add_argument("--run-id", required=True)
    runbook.add_argument("--max-steps", type=int, default=20)
    runbook.add_argument("--trace")

    supervise = sub.add_parser("supervise", help="Start supervisor runbook team run")
    _add_common_args(supervise)
    supervise.add_argument("message")
    supervise.add_argument("--run-id", required=True)
    supervise.add_argument("--max-steps", type=int, default=20)
    supervise.add_argument("--trace")

    resume = sub.add_parser("resume", help="Resume a paused run")
    _add_common_args(resume)
    resume.add_argument("--run-id", required=True)
    resume.add_argument("--max-steps", type=int, default=20)
    resume.add_argument("--trace")

    explain = sub.add_parser("explain", help="Explain a run (audit trail)")
    _add_common_args(explain)
    explain.add_argument("--run-id", required=True)

    approve = sub.add_parser("approve", help="Approve a paused run awaiting HITL")
    _add_common_args(approve)
    approve.add_argument("--run-id", required=True)
    approve.add_argument("--note", default="LGTM")
    approve.add_argument("--role", default=None, help="Agent role (planner|executor|verifier)")
    approve.add_argument("--max-steps", type=int, default=20)

    serve = sub.add_parser("serve", help="Start HTTP server (SSE /runbook, /supervise)")
    _add_common_args(serve)
    serve.add_argument("--host", default=os.environ.get("LOOM_OPS_HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.environ.get("LOOM_OPS_PORT", "8766")))

    telegram_cmd = sub.add_parser("telegram", help="Start Telegram bot gateway (requires telegram extra)")
    _add_common_args(telegram_cmd)

    return parser.parse_args(argv)


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", default=os.environ.get("LOOM_OPS_DB", "ops.sqlite"))
    parser.add_argument("--mock-llm", action="store_true", default=False)
    parser.add_argument("--max-tool-calls", type=int, default=None)
    parser.add_argument("--mcp-config", default=os.environ.get("LOOM_OPS_MCP_CONFIG"))
    parser.add_argument("--workspace", default=os.environ.get("LOOM_OPS_WORKSPACE"))


def _settings_from_args(args: argparse.Namespace) -> Settings:
    if args.workspace:
        os.environ["LOOM_OPS_WORKSPACE"] = str(Path(args.workspace).resolve())
    if args.mcp_config:
        os.environ["LOOM_OPS_MCP_CONFIG"] = str(Path(args.mcp_config).resolve())
    if args.max_tool_calls is not None:
        os.environ["LOOM_OPS_MAX_TOOL_CALLS"] = str(args.max_tool_calls)
    if args.command in {"runbook", "supervise"}:
        os.environ["LOOM_OPS_USER_MESSAGE"] = args.message
    if getattr(args, "mock_llm", False):
        os.environ["LOOM_OPS_MOCK_LLM"] = "1"
    settings = load_settings()
    if args.command in {"runbook", "supervise"} and not settings.user_message:
        settings = Settings(
            workspace=settings.workspace,
            mock_llm=settings.mock_llm,
            openai_api_key=settings.openai_api_key,
            openai_model=settings.openai_model,
            max_tool_calls=args.max_tool_calls or settings.max_tool_calls,
            user_message=args.message,
            mcp_config_path=settings.mcp_config_path,
            allow_shell=settings.allow_shell,
            shell_allowlist_path=settings.shell_allowlist_path,
            shell_timeout_sec=settings.shell_timeout_sec,
            memory_enabled=settings.memory_enabled,
        )
    return settings


def _run_telegram(args: argparse.Namespace) -> int:
    if args.workspace:
        os.environ["LOOM_OPS_WORKSPACE"] = str(Path(args.workspace).resolve())
    if getattr(args, "mock_llm", False):
        os.environ["LOOM_OPS_MOCK_LLM"] = "1"
    settings = load_settings()
    try:
        from loom_ops.telegram_bot import run_polling
    except ImportError as exc:
        raise SystemExit("install telegram extra: pip install 'loom-ops[telegram]'") from exc

    asyncio.run(run_polling(settings=settings, db_path=args.db))
    return 0


def _run_serve(args: argparse.Namespace) -> int:
    if args.workspace:
        os.environ["LOOM_OPS_WORKSPACE"] = str(Path(args.workspace).resolve())
    if args.mcp_config:
        os.environ["LOOM_OPS_MCP_CONFIG"] = str(Path(args.mcp_config).resolve())
    if getattr(args, "mock_llm", False):
        os.environ["LOOM_OPS_MOCK_LLM"] = "1"
    settings = load_settings()
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("install api extra: pip install 'loom-ops[api]'") from exc
    from loom_ops.http import create_app

    app = create_app(args.db, settings)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        from dataclasses import asdict

        return asdict(value)
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import asdict
from typing import Any

from pydantic import BaseModel, Field

from loom_ops.agents.runbook_agent import build_runner_with_settings, make_initial_state
from loom_ops.agents.supervisor_agent import (
    build_supervisor_runner,
    make_supervisor_initial_state,
)
from loom_ops.config import Settings


class RunbookRequest(BaseModel):
    message: str
    run_id: str
    max_steps: int = Field(default=20, ge=1)
    max_tool_calls: int | None = None


class SuperviseRequest(BaseModel):
    message: str
    run_id: str
    max_steps: int = Field(default=20, ge=1)
    max_tool_calls: int | None = None


def create_app(db_path: str, settings: Settings) -> Any:
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse, StreamingResponse
    except ImportError as exc:
        raise RuntimeError("install loom-ops with api extra: pip install 'loom-ops[api]'") from exc

    app = FastAPI(title="loom-ops", version="0.2.1")
    runner = build_runner_with_settings(db_path, settings)
    supervisor = build_supervisor_runner(db_path, settings)

    async def runbook_events(body: RunbookRequest) -> AsyncIterator[str]:
        state = make_initial_state(body.message, max_tool_calls=body.max_tool_calls)
        yield _format_sse("started", {"run_id": body.run_id, "message": body.message})

        remaining = body.max_steps
        result = await runner.start(run_id=body.run_id, initial_state=state, max_steps=1)
        remaining -= 1
        yield _format_sse("step", _result_payload(result))

        while result.status == "paused" and remaining > 0:
            result = await runner.resume(run_id=body.run_id, max_steps=1)
            remaining -= 1
            yield _format_sse("step", _result_payload(result))

        yield _format_sse(_terminal_event(result), _result_payload(result))

    async def supervise_events(body: SuperviseRequest) -> AsyncIterator[str]:
        state = make_supervisor_initial_state(
            body.run_id,
            body.message,
            max_tool_calls=body.max_tool_calls,
        )
        yield _format_sse("started", {"run_id": body.run_id, "message": body.message})

        remaining = body.max_steps
        result = await supervisor.start(run_id=body.run_id, initial_state=state, max_steps=1)
        remaining -= 1
        yield _format_sse("step", _result_payload(result))

        while result.status == "paused" and remaining > 0:
            result = await supervisor.resume(run_id=body.run_id, max_steps=1)
            remaining -= 1
            yield _format_sse("step", _result_payload(result))

        yield _format_sse(_terminal_event(result), _result_payload(result))

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat")
    async def chat(body: RunbookRequest) -> StreamingResponse:
        return StreamingResponse(runbook_events(body), media_type="text/event-stream")

    @app.post("/runbook")
    async def runbook(body: RunbookRequest) -> StreamingResponse:
        return StreamingResponse(runbook_events(body), media_type="text/event-stream")

    @app.post("/supervise")
    async def supervise(body: SuperviseRequest) -> StreamingResponse:
        return StreamingResponse(supervise_events(body), media_type="text/event-stream")

    @app.get("/runs/{run_id}/explain")
    async def explain_run(run_id: str) -> JSONResponse:
        explained = runner.explain_run(run_id)
        return JSONResponse(content=json.loads(json.dumps(_to_jsonable(explained), default=str)))

    return app


def _terminal_event(result: Any) -> str:
    if result.status == "completed":
        return "completed"
    if result.status == "paused":
        return "paused"
    return "error"


def _result_payload(result: Any) -> dict[str, Any]:
    data = asdict(result)
    if data.get("result") is not None:
        data["result"] = dict(data["result"])
    return data


def _format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value

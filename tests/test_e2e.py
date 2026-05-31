"""End-to-end tests: subprocess invoking loom-ops CLI."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from loom_ops.http import create_app
from tests.conftest import make_test_settings


def _run_cli(db: str, workspace: str, *args: str) -> dict:
    cmd = [
        sys.executable,
        "-m",
        "loom_ops.cli",
        *args,
        "--db",
        db,
        "--workspace",
        workspace,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, (
        f"command failed: {' '.join(cmd)}\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}"
    )
    return json.loads(result.stdout)


def test_e2e_runbook_completes(ops_workspace: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "ops.sqlite")
        ws = str(ops_workspace)
        out = _run_cli(
            db,
            ws,
            "runbook",
            "incident: API latency spike",
            "--run-id",
            "rb-001",
            "--mock-llm",
        )
        assert out["status"] == "completed"
        assert "Runbook complete" in out["result"]["answer"]


def test_e2e_supervise_three_subagents(ops_workspace: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "ops.sqlite")
        ws = str(ops_workspace)
        parent = _run_cli(
            db,
            ws,
            "supervise",
            "incident: API latency spike",
            "--run-id",
            "inc-001",
            "--mock-llm",
        )
        assert parent["status"] == "completed"
        assert "Supervisor merged" in parent["result"]["answer"]

        verifier = _run_cli(db, ws, "explain", "--run-id", "inc-001:sub:verifier")
        assert verifier["run_id"] == "inc-001:sub:verifier"
        assert verifier["tool_call_count"] >= 1


def test_e2e_pause_resume_explain(ops_workspace: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "ops.sqlite")
        ws = str(ops_workspace)

        paused = _run_cli(
            db,
            ws,
            "runbook",
            "incident: API latency spike",
            "--run-id",
            "rb-002",
            "--mock-llm",
            "--max-steps",
            "1",
        )
        assert paused["status"] == "paused"

        completed = _run_cli(
            db,
            ws,
            "resume",
            "--run-id",
            "rb-002",
            "--mock-llm",
            "--max-steps",
            "20",
        )
        assert completed["status"] == "completed"

        explained = _run_cli(db, ws, "explain", "--run-id", "rb-002")
        assert explained["status"] == "completed"
        assert explained["tool_call_count"] >= 1


def test_e2e_trace_html(ops_workspace: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db = str(tmp_path / "ops.sqlite")
        trace_path = tmp_path / "trace.html"
        ws = str(ops_workspace)

        out = _run_cli(
            db,
            ws,
            "supervise",
            "incident: API latency spike",
            "--run-id",
            "inc-trace",
            "--mock-llm",
            "--trace",
            str(trace_path),
        )
        assert out["status"] == "completed"
        assert trace_path.is_file()
        assert trace_path.stat().st_size > 0


@pytest.mark.asyncio
async def test_e2e_http_supervise_sse(ops_workspace: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "ops.sqlite")
        settings = make_test_settings(ops_workspace, user_message="")
        app = create_app(db, settings)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with client.stream(
                "POST",
                "/supervise",
                json={
                    "message": "incident: API latency spike",
                    "run_id": "http-inc",
                    "max_steps": 20,
                },
            ) as response:
                assert response.status_code == 200
                body = "".join([chunk async for chunk in response.aiter_text()])

            assert "event: started" in body
            assert "event: completed" in body

            explain_resp = await client.get("/runs/http-inc/explain")
            assert explain_resp.status_code == 200
            data = explain_resp.json()
            assert data["status"] == "completed"

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from loom_ops.agents.supervisor_agent import build_supervisor_runner, make_supervisor_initial_state
from loom_ops.approve import inject_approval_and_resume
from loom_ops.agents.runbook_agent import build_runner_with_settings
from loom_ops.config import Settings


@dataclass(frozen=True)
class TelegramConfig:
    token: str
    allowed_chat_ids: frozenset[int]


def load_telegram_config() -> TelegramConfig:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is required")
    raw_ids = os.environ.get("TELEGRAM_ALLOWED_CHAT_IDS", "").strip()
    if not raw_ids:
        raise ValueError("TELEGRAM_ALLOWED_CHAT_IDS is required (comma-separated)")
    chat_ids = frozenset(int(item.strip()) for item in raw_ids.split(",") if item.strip())
    return TelegramConfig(token=token, allowed_chat_ids=chat_ids)


def parse_command(text: str) -> tuple[str, list[str]]:
    stripped = text.strip()
    if not stripped.startswith("/"):
        return "", []
    parts = stripped.split()
    command = parts[0].split("@")[0].lower()
    return command, parts[1:]


async def handle_message(
    *,
    chat_id: int,
    text: str,
    settings: Settings,
    db_path: str,
    config: TelegramConfig,
) -> str:
    if chat_id not in config.allowed_chat_ids:
        return "chat not allowed"

    command, args = parse_command(text)
    if command == "/supervise":
        message = " ".join(args) or settings.user_message or "incident response"
        run_id = _next_run_id("tg")
        return await _run_supervise(settings, db_path, run_id=run_id, message=message)
    if command == "/approve":
        if len(args) < 1:
            return "usage: /approve <run_id> [note]"
        run_id = args[0]
        note = " ".join(args[1:]) if len(args) > 1 else "LGTM"
        return await _run_approve(settings, db_path, run_id=run_id, note=note)
    if command == "/explain":
        if not args:
            return "usage: /explain <run_id>"
        return _run_explain(settings, db_path, run_id=args[0])
    return "commands: /supervise <msg>, /approve <run_id> [note], /explain <run_id>"


async def _run_supervise(settings: Settings, db_path: str, *, run_id: str, message: str) -> str:
    runner = build_supervisor_runner(db_path, settings)
    state = make_supervisor_initial_state(run_id, message, settings=settings)
    result = await runner.start(run_id=run_id, initial_state=state, max_steps=20)
    answer = ""
    if result.result:
        answer = str(result.result.get("answer", ""))[:500]
    return f"run_id={run_id} status={result.status}\n{answer}"


async def _run_approve(settings: Settings, db_path: str, *, run_id: str, note: str) -> str:
    result = await inject_approval_and_resume(
        db_path,
        settings,
        run_id=run_id,
        note=note,
        max_steps=20,
        role=None,
    )
    answer = ""
    if result.result:
        answer = str(result.result.get("answer", ""))[:300]
    return f"run_id={run_id} status={result.status}\n{answer}"


def _run_explain(settings: Settings, db_path: str, *, run_id: str) -> str:
    runner = build_runner_with_settings(db_path, settings)
    explained = runner.explain_run(run_id)
    payload = {
        "run_id": explained.run_id,
        "status": explained.status,
        "tool_call_count": explained.tool_call_count,
    }
    return json.dumps(payload, indent=2)


def _next_run_id(prefix: str) -> str:
    import uuid

    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class TelegramClient:
    def __init__(self, config: TelegramConfig, *, http_client: Any = None) -> None:
        self._config = config
        self._http = http_client
        self._base = f"https://api.telegram.org/bot{config.token}"

    async def _client(self) -> Any:
        if self._http is not None:
            return self._http
        import httpx

        return httpx.AsyncClient(timeout=30.0)

    async def send_message(self, chat_id: int, text: str) -> None:
        client = await self._client()
        owns = self._http is None
        try:
            response = await client.post(
                f"{self._base}/sendMessage",
                json={"chat_id": chat_id, "text": text[:4000]},
            )
            response.raise_for_status()
        finally:
            if owns:
                await client.aclose()

    async def get_updates(self, offset: int | None = None) -> list[dict[str, Any]]:
        client = await self._client()
        owns = self._http is None
        params: dict[str, Any] = {"timeout": 0}
        if offset is not None:
            params["offset"] = offset
        try:
            response = await client.get(f"{self._base}/getUpdates", params=params)
            response.raise_for_status()
            data = response.json()
            return list(data.get("result", []))
        finally:
            if owns:
                await client.aclose()


async def run_polling(
    *,
    settings: Settings,
    db_path: str,
    config: TelegramConfig | None = None,
) -> None:
    cfg = config or load_telegram_config()
    client = TelegramClient(cfg)
    offset: int | None = None
    while True:
        updates = await client.get_updates(offset=offset)
        for update in updates:
            offset = int(update["update_id"]) + 1
            message = update.get("message") or {}
            chat = message.get("chat") or {}
            chat_id = int(chat.get("id", 0))
            text = str(message.get("text", ""))
            if not text:
                continue
            reply = await handle_message(
                chat_id=chat_id,
                text=text,
                settings=settings,
                db_path=db_path,
                config=cfg,
            )
            await client.send_message(chat_id, reply)

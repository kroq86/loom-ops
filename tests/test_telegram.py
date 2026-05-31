from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom_ops.telegram_bot import (
    TelegramConfig,
    handle_message,
    load_telegram_config,
    parse_command,
)
from tests.conftest import make_test_settings


def test_parse_command() -> None:
    assert parse_command("/supervise api down") == ("/supervise", ["api", "down"])
    assert parse_command("/approve exec-1 LGTM") == ("/approve", ["exec-1", "LGTM"])
    assert parse_command("hello") == ("", [])


def test_load_telegram_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_IDS", "42,99")
    cfg = load_telegram_config()
    assert cfg.token == "test-token"
    assert cfg.allowed_chat_ids == frozenset({42, 99})


@pytest.mark.asyncio
async def test_handle_message_rejects_chat(ops_workspace: Path) -> None:
    settings = make_test_settings(ops_workspace)
    cfg = TelegramConfig(token="t", allowed_chat_ids=frozenset({1}))
    reply = await handle_message(
        chat_id=999,
        text="/supervise incident",
        settings=settings,
        db_path=":memory:",
        config=cfg,
    )
    assert reply == "chat not allowed"


@pytest.mark.asyncio
async def test_handle_supervise_command(ops_workspace: Path, tmp_path: Path) -> None:
    settings = make_test_settings(ops_workspace)
    cfg = TelegramConfig(token="t", allowed_chat_ids=frozenset({1}))
    db = str(tmp_path / "tg.sqlite")
    reply = await handle_message(
        chat_id=1,
        text="/supervise incident: latency",
        settings=settings,
        db_path=db,
        config=cfg,
    )
    assert "status=completed" in reply
    assert "run_id=tg-" in reply


@pytest.mark.asyncio
async def test_telegram_client_send_message() -> None:
    from loom_ops.telegram_bot import TelegramClient

    mock_http = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_http.post = AsyncMock(return_value=mock_response)
    mock_http.aclose = AsyncMock()

    client = TelegramClient(TelegramConfig(token="tok", allowed_chat_ids=frozenset()), http_client=mock_http)
    await client.send_message(1, "ok")
    mock_http.post.assert_awaited_once()
    args, kwargs = mock_http.post.await_args
    assert "sendMessage" in args[0]
    assert kwargs["json"]["text"] == "ok"

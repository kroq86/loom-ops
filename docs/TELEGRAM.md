# Telegram gateway

Optional integration to trigger supervisor runs and approvals from Telegram.

## Install

```bash
pip install -e ".[telegram]"
```

## Environment

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_ALLOWED_CHAT_IDS` | Comma-separated chat IDs allowed to invoke commands |

Also set standard loom-ops vars (`LOOM_OPS_WORKSPACE`, `LOOM_OPS_DB`, `LOOM_OPS_MOCK_LLM` for CI-safe runs).

## Run

```bash
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_ALLOWED_CHAT_IDS=123456789
loom-ops telegram --db ops.sqlite --mock-llm --workspace .
```

## Commands

| Command | Action |
|---------|--------|
| `/supervise <message>` | Start supervisor run; replies with `run_id` and status |
| `/approve <run_id> [note]` | Approve paused HITL child run |
| `/explain <run_id>` | JSON summary from checkpoint store |

## Security

- Reject all chats not listed in `TELEGRAM_ALLOWED_CHAT_IDS`.
- Do not expose the bot token in logs or commits.
- Prefer running alongside mock LLM until OpenAI prompts are reviewed for your environment.

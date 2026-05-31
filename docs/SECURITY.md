# Security

## Defaults (safe)

- **Mock execution** — `execute_step` logs actions unless `LOOM_OPS_ALLOW_SHELL=1`.
- **Allowlisted shell** — when enabled, only command prefixes in `ops.shell.allowlist.json` run via subprocess (no `python -c`).
- **Workspace-bound runbooks** — `read_runbook` cannot escape `runbooks/`.
- **HITL** — destructive steps use `await_approval`; human runs `loom-ops approve`.
- **Telegram** — requires `TELEGRAM_ALLOWED_CHAT_IDS`; unknown chats get `chat not allowed`.
- **MCP** — child processes do not inherit `OPENAI_*`, `TELEGRAM_*`, `AWS_*`, `PYPI_*`, or GitHub token env vars from the parent.

## HTTP API (`loom-ops serve`)

- Endpoints: `/chat`, `/runbook`, `/supervise`, `/runs/{run_id}/explain`.
- **No authentication** in v0.2.x — any client that can reach the bind address can start runs and read checkpoints.
- Default bind: `127.0.0.1:8766` (`LOOM_OPS_HOST` / `LOOM_OPS_PORT`).
- **Do not** expose `0.0.0.0` on a network without a reverse proxy, TLS, and an API gate.

## Workspace memory

- `workspace/.loom-ops/memory.jsonl` stores recent runbook/audit snippets for prompt context.
- Treat this file as **confidential** (may echo incident text). Delete or rotate if a workspace is shared or archived.

## Before enabling real execution

1. Replace the sample allowlist with commands you actually need.
2. Run under a least-privileged OS user.
3. Review MCP server provenance before `LOOM_OPS_MCP_CONFIG`.
4. Keep SQLite (`LOOM_OPS_DB`) and flow-xray HTML traces off shared drives without encryption.

## Comparison

Unlike agents with broad shell access, loom-ops defaults to **mock + audit**. Real shell and MCP are opt-in.

# Security

## Phase 1 (current)

- **Mock execution by default** — `execute_step` logs actions unless `LOOM_OPS_ALLOW_SHELL=1`.
- **Allowlisted shell** — when enabled, only command prefixes listed in `ops.shell.allowlist.json` run via subprocess.
- **Workspace-bound runbooks** — `read_runbook` cannot escape `runbooks/`.
- **HITL** — destructive steps use `await_approval`; human runs `loom-ops approve`.

## Before enabling real execution

1. Set explicit allowlist for commands and targets
2. Run under least-privileged OS user
3. Never expose HTTP server to public internet without auth
4. Review MCP server provenance before connecting ops tools

## Comparison

Unlike OpenClaw-style personal agents with broad shell access, loom-ops defaults to **mock + audit**. Real ops MCP is opt-in via `LOOM_OPS_MCP_CONFIG`.

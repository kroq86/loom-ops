# Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOOM_OPS_WORKSPACE` | cwd | Root containing `runbooks/` |
| `LOOM_OPS_DB` | `ops.sqlite` | SQLite checkpoint database |
| `LOOM_OPS_MOCK_LLM` | `1` | Use deterministic mock LLM (CI-safe) |
| `LOOM_OPS_MAX_TOOL_CALLS` | `10` | Tool budget per run |
| `LOOM_OPS_MCP_CONFIG` | — | Path to MCP servers JSON |
| `LOOM_OPS_ALLOW_SHELL` | — | Set `1` to enable allowlisted shell in `execute_step` |
| `LOOM_OPS_SHELL_ALLOWLIST` | `workspace/ops.shell.allowlist.json` | JSON file with allowed command prefixes |
| `LOOM_OPS_SHELL_TIMEOUT_SEC` | `30` | Max seconds per shell command |
| `LOOM_OPS_MEMORY` | `1` | Append runbook/audit snippets to `workspace/.loom-ops/memory.jsonl` and inject into new runs |
| `LOOM_OPS_OPENAI` | — | Set `1` + `OPENAI_API_KEY` for OpenAI supervisor/runbook LLM |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model |
| `LOOM_OPS_HOST` | `127.0.0.1` | HTTP server bind host |
| `LOOM_OPS_PORT` | `8766` | HTTP server port |

## OpenAI mode

```bash
export LOOM_OPS_MOCK_LLM=0
export LOOM_OPS_OPENAI=1
export OPENAI_API_KEY=sk-...
loom-ops supervise "incident: db failover" --run-id inc-002 --workspace .
```

Mock LLM remains default for CI (`python -m pytest -q`).

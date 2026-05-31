# loom-ops

**Durable runbook ops agent** on the [Loom stack](https://kroq86.github.io/loom-stack/) — ops sibling of [loom-run](https://github.com/kroq86/loom-run), built on [loom-runner](https://github.com/kroq86/loom-runner) with [flow-xray](https://github.com/kroq86/flow-xray) traces.

> Run нельзя потерять: упал на шаге 12/40 → `resume`, каждый tool call в SQLite, postmortem через `explain` + flow-xray.

## Loom stack (this repo’s place)

| Package | Role |
|---------|------|
| [loom-stack hub](https://kroq86.github.io/loom-stack/) | Start here — docs and comparisons |
| [loom-runner](https://github.com/kroq86/loom-runner) | **Runtime** — checkpoint/resume (dependency) |
| [loom-run](https://github.com/kroq86/loom-run) | **Showcase** — dev chat on a repo |
| **loom-ops** | **Product** — incident/deploy runbooks (this repo) |
| [flow-xray](https://github.com/kroq86/flow-xray) | **Traces** — `--trace` HTML graphs |

Full map: [docs/STACK.md](docs/STACK.md). Dev assistant → use **loom-run**; ops runbooks → **loom-ops**.

## Install

**From PyPI** (runtime + CLI):

```bash
pip install "loom-ops[api,telegram]"
loom-ops supervise "incident: API latency spike" --run-id inc-001 --db ops.sqlite --mock-llm --workspace .
```

**From source** (development):

```bash
git clone https://github.com/kroq86/loom-ops.git
cd loom-ops
python3.13 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,api,telegram]"
```

## Demo (mock LLM, no API key)

```bash
# Supervisor team: planner → parallel executor + verifier
loom-ops supervise "incident: API latency spike" --run-id inc-001 --db ops.sqlite --mock-llm --workspace .

# Inspect verifier subagent audit trail
loom-ops explain --run-id inc-001:sub:verifier --db ops.sqlite --workspace .

# Single runbook walk
loom-ops runbook "incident: API latency spike" --run-id rb-001 --db ops.sqlite --mock-llm --workspace .

# HITL: executor pauses for approval (see tests/test_supervisor_ops.py)
loom-ops approve --run-id exec-1 --note "LGTM" --role executor --db ops.sqlite --mock-llm --workspace .

# Allowlisted shell (optional)
export LOOM_OPS_ALLOW_SHELL=1
# uses workspace/ops.shell.allowlist.json by default
loom-ops runbook "deploy check" --run-id rb-shell --db ops.sqlite --mock-llm --workspace .

# HTTP SSE
loom-ops serve --db ops.sqlite --mock-llm --workspace .
curl -N -X POST http://127.0.0.1:8766/supervise \
  -H 'Content-Type: application/json' \
  -d '{"message":"incident: API latency spike","run_id":"inc-http","max_steps":20}'
curl http://127.0.0.1:8766/runs/inc-http/explain

# Telegram gateway (optional extra)
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_ALLOWED_CHAT_IDS=123456789
loom-ops telegram --db ops.sqlite --mock-llm --workspace .
```

## Ops tools

| Tool | Role | Purpose |
|------|------|---------|
| `read_runbook` | planner | Load runbook from `runbooks/` |
| `execute_step` | executor | Mock, allowlisted shell, or MCP |
| `await_approval` | executor | HITL gate — run pauses until `approve` |
| `check_health` | verifier | Service health check (mock / MCP) |
| `record_audit` | verifier | Append audit entry (+ workspace memory) |
| `delegate_subagent` | supervisor | Spawn single resumable child run |
| `delegate_subagents_batch` | supervisor | Run multiple child roles in parallel |

## Docs

- [Loom stack integration](docs/STACK.md)
- [Product positioning](docs/PRODUCT.md)
- [Runbooks](docs/RUNBOOKS.md)
- [Environment variables](docs/ENV.md)
- [Security](docs/SECURITY.md)
- [Telegram gateway](docs/TELEGRAM.md)

## Tests

```bash
python -m pytest -q
```

## License

MIT

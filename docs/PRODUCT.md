# Product positioning — loom-ops

## One-liner

**Durable runbook ops agent** — local-first incident/deploy automation where checkpoint/resume and audit trail matter more than 24/7 chat.

## What loom-ops is

Part of the [Loom stack](https://kroq86.github.io/loom-stack/) — see [STACK.md](STACK.md) for repo map and install order.

| | |
|---|---|
| **Product fork** | Ops/runbook agent built on loom-runner |
| **Showcase sibling** | [loom-run](https://github.com/kroq86/loom-run) stays the official Loom stack demo (dev chat + minimal supervisor) |
| **Runtime** | [loom-runner](https://github.com/kroq86/loom-runner) SQLite checkpoint/resume |
| **Traces** | [flow-xray](https://github.com/kroq86/flow-xray) offline HTML |
| **Hub** | [loom-stack docs](https://kroq86.github.io/loom-stack/) — cross-links all repos |

## vs OpenClaw / Hermes

| | OpenClaw / Hermes | loom-ops |
|---|-------------------|----------|
| Primary UX | Personal assistant in messengers | CLI / HTTP / optional Telegram for runbooks |
| Memory | Long-term user memory, skills | Per-run checkpoint + workspace `memory.jsonl` |
| Durability | Session-based | SQLite checkpoint every step |
| Audit | Limited | `explain` + trace HTML |
| AGI | Marketing hype | **No claim** |

## vs loom-run showcase

| | loom-run | loom-ops |
|---|----------|----------|
| Domain | Dev repo (read/search/tests) | Ops runbooks |
| Supervisor roles | researcher (demo) | planner / executor / verifier |
| Tools | dev + MCP verifier | ops + HITL + ops MCP preset |
| CLI | `loom-run chat` | `loom-ops supervise` / `runbook` |

## Honest scope (v0.2)

**Shipped:** mock LLM, parallel supervisor (planner → executor+verifier batch), allowlisted shell `execute_step`, unified workspace memory, HITL approve, HTTP `/supervise`, optional Telegram gateway, audit `/runs/{id}/explain`.

**Deferred:** HTTP auth, OpenAI-tuned parallel prompts, production kubectl/rollback in CI examples.

## Keywords

`loom-ops`, `runbook agent`, `durable ops`, `incident response`, `checkpoint resume`, `HITL agent`, `audit trail`, `loom stack`

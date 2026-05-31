# AGENTS.md — loom-ops

Human owns architecture and stop decisions. AI is a junior pair.

## Scope

- One small change per request: one module, test file, or integration step.
- Do not port all of `agents_architecture` into this repo.
- **loom-ops** wires ops coordinator + tools + **loom-runner**; [loom-run](https://github.com/kroq86/loom-run) and [flow-xray](https://github.com/kroq86/flow-xray) stay sibling repos (see [docs/STACK.md](docs/STACK.md)).

## Loop

1. Human defines boundary.
2. Propose tiny change with why + test.
3. Run `python -m pytest -q` in this repo.
4. Two failed fix attempts on the same issue → stop; human debugs.

## Invariants

- Mock LLM must keep CI green without API keys.
- Tools must work with local fallbacks when MCP is not configured.
- Managed side effects go through `RunContext.call_tool(...)`.
- Durable semantics come from **loom-runner**; do not reimplement checkpoint/resume here.

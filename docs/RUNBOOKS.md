# Runbooks

Runbooks live in `runbooks/` under your workspace (`--workspace` or `LOOM_OPS_WORKSPACE`).

## Bundled example

[`runbooks/incident-response.md`](../runbooks/incident-response.md):

1. Triage — confirm severity
2. Isolate — reduce blast radius
3. Rollback — revert deployment (destructive → HITL)
4. Verify — health checks
5. Postmortem — audit trail

## Mock LLM scenarios

| Role | Deterministic tool sequence |
|------|----------------------------|
| planner | `read_runbook(incident-response.md)` → finish |
| executor | `execute_step(rollback)` → `await_approval` → finish after approve |
| verifier | `check_health` → `record_audit` → finish |
| supervisor (v0.2) | delegate planner → `delegate_subagents_batch(executor, verifier)` → merge |
| full runbook | read → execute → check → audit |

## Adding runbooks

1. Create `runbooks/your-playbook.md` in workspace
2. Reference by name in prompts or extend MockOpsLLM / OpenAI prompts
3. Keep destructive steps documented for HITL gates

## MCP (optional)

When [data-engineering-runtime-lab](https://github.com/kroq86/data-engineering-runtime-lab) MCP is configured, `execute_step` and `check_health` can delegate to real ops tools. See [`mcp.servers.example.json`](../mcp.servers.example.json).

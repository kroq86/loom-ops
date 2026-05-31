# Incident Response Runbook

## Trigger
API latency spike or elevated error rate on production services.

## Steps

1. **Triage** — Confirm alert severity, identify affected service and time window.
2. **Isolate** — Reduce blast radius (rate limit, drain bad instances, feature flag).
3. **Rollback** — Revert last deployment if change correlated with incident start.
4. **Verify** — Health checks green; latency and error rate back to baseline.
5. **Postmortem** — Record timeline, root cause hypothesis, and follow-up actions.

## Destructive actions
- Rollback requires human approval before execution.

## Success criteria
- All health checks pass for 15 minutes.
- Audit log contains triage → isolate → rollback → verify entries.

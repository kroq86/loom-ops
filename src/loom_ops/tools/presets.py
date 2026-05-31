"""MCP server presets mapping loom-ops tool names to external MCP tool names."""

VERIFIER_PRESET = {
    "run_tests": "run_tests",
    "read_file": "read_repo_file",
}

DOCS_MEMORY_PRESET = {
    "search_docs": "docs_search",
}

OPS_RUNTIME_PRESET = {
    "execute_step": "execute_runbook_step",
    "check_health": "check_service_health",
}

PRESETS = {
    "rule-based-verifier": VERIFIER_PRESET,
    "docs-memory": DOCS_MEMORY_PRESET,
    "data-engineering-runtime-lab": OPS_RUNTIME_PRESET,
}

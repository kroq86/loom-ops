from __future__ import annotations

from loom_ops.supervisor.llm_impl import MockOpsSupervisorLLM, create_supervisor_llm
from loom_ops.tools.presets import OPS_RUNTIME_PRESET, PRESETS


def test_ops_mcp_preset_registered() -> None:
    assert "data-engineering-runtime-lab" in PRESETS
    assert PRESETS["data-engineering-runtime-lab"] == OPS_RUNTIME_PRESET
    assert "execute_step" in OPS_RUNTIME_PRESET
    assert "check_health" in OPS_RUNTIME_PRESET


def test_create_supervisor_llm_mock() -> None:
    llm = create_supervisor_llm(mock_llm=True, openai_api_key=None, openai_model="gpt-4o-mini")
    assert isinstance(llm, MockOpsSupervisorLLM)

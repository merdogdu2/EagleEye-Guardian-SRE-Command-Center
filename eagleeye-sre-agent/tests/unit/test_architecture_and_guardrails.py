# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for composition root (<100 lines), AGENTS.md (<8KB), plugins, and guardrails."""

from __future__ import annotations

import json
import pathlib

from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai.types import Content, Part

from app.agent import app, root_agent
from app.core.a2ui.primitives import A2UI_OPEN_TAG, wrap_a2ui_part
from app.core.a2ui.surfaces import build_incident_triage_surface
from app.core.config import AGENTS_MD_MAX_BYTES, MAX_TOOL_OUTPUT_BYTES
from app.core.guardrails import (
    after_model_callback,
    before_model_call,
    enforce_tool_output_budget,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]


def test_composition_root_under_100_lines() -> None:
    """Enforce that app/agent.py stays strictly under 100 lines."""
    agent_py = REPO_ROOT / "eagleeye-sre-agent" / "app" / "agent.py"
    line_count = len(agent_py.read_text(encoding="utf-8").splitlines())
    assert line_count < 100, f"app/agent.py must be < 100 lines, got {line_count}"


def test_agents_md_under_8_kb() -> None:
    """Enforce that AGENTS.md is strictly under 8 KB (8,192 bytes)."""
    agents_md = REPO_ROOT / "AGENTS.md"
    assert agents_md.is_file(), "AGENTS.md must exist at repository root"
    size_bytes = len(agents_md.read_bytes())
    assert size_bytes < AGENTS_MD_MAX_BYTES, (
        f"AGENTS.md must be < {AGENTS_MD_MAX_BYTES} bytes, got {size_bytes}"
    )


def test_adk_app_wiring_and_subagents() -> None:
    """Verify root_agent delegates to 4 specialist sub-agents and App configures all plugins."""
    assert app.name == "eagleeye_guardian_sre"
    assert app.root_agent is root_agent
    assert app.context_cache_config is not None
    assert app.events_compaction_config is not None
    assert app.resumability_config is not None and app.resumability_config.is_resumable is True

    sub_names = [sa.name for sa in root_agent.sub_agents]
    assert sub_names == [
        "incident_triage_agent",
        "capacity_shield_agent",
        "database_reliability_agent",
        "security_guard_agent",
    ]
    plugin_names = [p.name for p in app.plugins]
    assert "bigquery_agent_analytics" in plugin_names
    assert "safety_and_a2ui_plugin" in plugin_names


def test_tool_output_budget_guardrail() -> None:
    """Verify enforce_tool_output_budget caps oversized dictionaries at <= 16 KB."""
    oversized = {
        "status": "OK",
        "summary": "Large telemetry dump",
        "huge_blob": "X" * 40_000,
    }
    compacted = enforce_tool_output_budget(oversized)
    encoded = json.dumps(compacted).encode("utf-8")
    assert len(encoded) <= MAX_TOOL_OUTPUT_BYTES
    assert compacted.get("truncated") is True


def test_before_model_call_sanitizes_prior_a2ui_parts() -> None:
    """Guardrail 9: Verify prior-turn A2UI JSON parts are replaced with concise text summaries."""
    prior_a2ui_part = wrap_a2ui_part(build_incident_triage_surface())
    req = LlmRequest(
        contents=[
            Content(role="user", parts=[Part.from_text(text="Show incident triage")]),
            Content(
                role="model",
                parts=[Part.from_text(text="Here is the incident card."), prior_a2ui_part],
            ),
            Content(role="user", parts=[Part.from_text(text="What is the current step?")]),
        ]
    )

    intercept = before_model_call(None, req)
    assert intercept is None

    model_turn_parts = req.contents[1].parts
    assert model_turn_parts is not None and len(model_turn_parts) == 2
    sanitized_part = model_turn_parts[1]
    assert sanitized_part.inline_data is None
    assert sanitized_part.text is not None
    assert "Prior-turn A2UI v0.9 surface rendered" in sanitized_part.text
    assert "sre-incident-triage-card" in sanitized_part.text


def test_after_model_callback_attaches_surface_and_handles_errors_gracefully() -> None:
    """Guardrail 10: Verify after_model_callback attaches A2UI Part and degrades gracefully on error."""
    resp = LlmResponse(
        content=Content(
            role="model",
            parts=[
                Part.from_text(
                    text="Detected ZONE_RESOURCE_POOL_EXHAUSTED in europe-west2-b [surface:incident]"
                )
            ],
        )
    )
    updated = after_model_callback(None, resp)
    assert updated is not None
    assert resp.content is not None and resp.content.parts is not None
    assert len(resp.content.parts) == 2
    assert A2UI_OPEN_TAG in (resp.content.parts[1].inline_data.data or b"")

    # Now test graceful degradation when surface builder raises an exception
    resp_err = LlmResponse(
        content=Content(role="model", parts=[Part.from_text(text="Prose response only")])
    )

    def _broken_builder() -> list[dict[str, object]]:
        raise RuntimeError("Simulated UI builder failure")

    fallback = after_model_callback(None, resp_err, force_surface_builder=_broken_builder)
    assert fallback is None
    assert len(resp_err.content.parts) == 1
    assert resp_err.content.parts[0].text == "Prose response only"

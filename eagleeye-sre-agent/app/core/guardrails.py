# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""ADK Plugins & Guardrails: history sanitization, 16KB tool budget, and graceful A2UI emission."""

from __future__ import annotations

import json
import logging
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from google.genai.types import Content, Part

from app.core.a2ui.a2a_bridge import install_a2a_bridge
from app.core.a2ui.actions import dispatch_a2ui_action, parse_inbound_a2ui_action
from app.core.a2ui.primitives import (
    A2UI_CLOSE_TAG,
    A2UI_MIME_TYPE,
    A2UI_OPEN_TAG,
    extract_a2ui_messages_from_part,
    wrap_a2ui_part,
)
from app.core.a2ui.surfaces import (
    build_fleet_finops_explorer_surface,
    build_hitl_confirmation_surface,
    build_incident_triage_surface,
    build_sre_command_center_iframe_surface,
)
from app.core.config import MAX_TOOL_OUTPUT_BYTES

logger = logging.getLogger(__name__)

install_a2a_bridge()


def enforce_tool_output_budget(
    payload: dict[str, Any], max_bytes: int = MAX_TOOL_OUTPUT_BYTES
) -> dict[str, Any]:
    """Ensure tool output JSON never exceeds the 16 KB (16,384 byte) context budget."""
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(serialized) <= max_bytes:
        return payload

    compact: dict[str, Any] = {
        "status": payload.get("status", "OK"),
        "truncated": True,
        "original_bytes": len(serialized),
        "budget_bytes": max_bytes,
    }
    for key, val in payload.items():
        if key in compact:
            continue
        candidate = {**compact, key: val}
        cand_bytes = json.dumps(candidate, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        if len(cand_bytes) <= max_bytes - 256:
            compact[key] = val
        elif isinstance(val, str):
            remaining = max(128, (max_bytes - len( serialized[:512])) // 2)
            compact[key] = val[:remaining] + "...[truncated]"
        elif isinstance(val, list) and val:
            compact[key] = val[:3]
    final_bytes = json.dumps(compact, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(final_bytes) > max_bytes:
        return {
            "status": payload.get("status", "OK"),
            "truncated": True,
            "summary": str(payload.get("summary", "Output truncated to enforce 16 KB budget."))[
                : max_bytes // 2
            ],
        }
    return compact


def _summarize_a2ui_part(part: Part) -> Part | None:
    """If part is an A2UI v0.9 payload, return a concise plain-text summary Part (Rule 9)."""
    messages = extract_a2ui_messages_from_part(part)
    if messages is not None:
        surface_ids: list[str] = []
        verbs: list[str] = []
        for item in messages:
            if isinstance(item, dict):
                for k, v in item.items():
                    if k != "version" and isinstance(v, dict):
                        verbs.append(k)
                        sid = v.get("surfaceId")
                        if isinstance(sid, str) and sid not in surface_ids:
                            surface_ids.append(sid)
        sid_str = ", ".join(surface_ids) if surface_ids else "default"
        verb_str = ", ".join(verbs) if verbs else "update"
        return Part.from_text(
            text=f"[Prior-turn A2UI v0.9 surface rendered: surfaceId={sid_str} ({verb_str})]"
        )

    if part.part_metadata and part.part_metadata.get("mimeType") == A2UI_MIME_TYPE:
        return Part.from_text(text="[Prior-turn A2UI v0.9 surface rendered]")

    if part.text and ("<a2a_datapart_json>" in part.text or '"createSurface"' in part.text):
        return Part.from_text(text="[Prior-turn A2UI v0.9 surface rendered in chat history]")

    return None


def before_model_call(
    callback_context: CallbackContext | None,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """Guardrail 9: Sanitize prior-turn A2UI JSON parts and intercept inbound a2ui_action events."""
    contents = getattr(llm_request, "contents", None) or []

    # 1. Inspect the latest user message for deterministic inbound a2ui_action payloads
    if contents:
        last_content = contents[-1]
        if getattr(last_content, "role", None) == "user" and getattr(last_content, "parts", None):
            for part in last_content.parts or []:
                inbound = None
                if part.text:
                    inbound = parse_inbound_a2ui_action(part.text)
                elif getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                    raw_bytes = part.inline_data.data
                    raw_str = (
                        raw_bytes.decode("utf-8", errors="ignore")
                        if isinstance(raw_bytes, (bytes, bytearray))
                        else str(raw_bytes)
                    )
                    open_tag = A2UI_OPEN_TAG.decode("utf-8")
                    close_tag = A2UI_CLOSE_TAG.decode("utf-8")
                    if raw_str.startswith(open_tag) and raw_str.endswith(close_tag):
                        raw_str = raw_str[len(open_tag) : -len(close_tag)]
                    inbound = parse_inbound_a2ui_action(raw_str)
                if inbound is not None:
                    dispatched = dispatch_a2ui_action(inbound)
                    response_parts: list[Part] = [Part.from_text(text=dispatched["summary"])]
                    try:
                        a2ui_part = wrap_a2ui_part(dispatched["a2ui_messages"])
                        response_parts.append(a2ui_part)
                    except Exception as exc:  # pragma: no cover
                        logger.warning("Graceful A2UI fallback on action dispatch: %s", exc)
                    return LlmResponse(
                        content=Content(role="model", parts=response_parts),
                    )

    # 2. Sanitize prior-turn A2UI parts in history so the LLM never echoes raw A2UI JSON in prose
    for content in contents:
        parts = getattr(content, "parts", None)
        if not parts:
            continue
        sanitized_parts: list[Part] = []
        for part in parts:
            replacement = _summarize_a2ui_part(part)
            sanitized_parts.append(replacement if replacement is not None else part)
        content.parts = sanitized_parts

    return None


history_callback = before_model_call


def _select_surface_for_text(text: str) -> list[dict[str, Any]] | None:
    """Select an A2UI v0.9 surface envelope based on the model's response or requested surface tag."""
    lower = text.lower()
    combined: list[dict[str, Any]] = []

    has_explicit_tag = any(
        tag in lower
        for tag in ("[surface:incident]", "[surface:hitl]", "[surface:explorer]", "[surface:workbench]")
    )
    if has_explicit_tag:
        if "[surface:incident]" in lower:
            combined.extend(build_incident_triage_surface())
        if "[surface:hitl]" in lower:
            combined.extend(build_hitl_confirmation_surface())
        if "[surface:explorer]" in lower:
            combined.extend(build_fleet_finops_explorer_surface())
        if "[surface:workbench]" in lower:
            combined.extend(build_sre_command_center_iframe_surface())
        return combined or None

    is_incident = (
        "zone_resource_pool_exhausted" in lower
        or "inc-2026" in lower
        or "p99 latency" in lower
        or "682.4" in lower
    )
    is_hitl = (
        "hitl confirmation" in lower
        or "approval required" in lower
        or "human-in-the-loop" in lower
        or "act-hd-scale-320k" in lower
    )
    is_explorer = (
        "rich_table" in lower
        or "richtable" in lower
        or "finops explorer" in lower
        or "idle standby" in lower
        or "n1 exit" in lower
    )
    is_workbench = (
        "command center" in lower
        or "sre workbench" in lower
        or "#s=z." in lower
        or "vpc service controls" in lower
        or "security_policy_violated" in lower
        or "cloud spanner" in lower
        or "rtx pro 6000" in lower
    )

    if is_incident:
        combined.extend(build_incident_triage_surface())
    if is_hitl:
        combined.extend(build_hitl_confirmation_surface())
    if is_workbench:
        active_tab = "capacity"
        if "vpc" in lower or "security_policy_violated" in lower:
            active_tab = "security"
        elif "spanner" in lower:
            active_tab = "spanner"
        elif "hyperdisk" in lower and not is_incident:
            active_tab = "hyperdisk"
        combined.extend(build_sre_command_center_iframe_surface(active_tab=active_tab))
    elif is_explorer:
        combined.extend(build_fleet_finops_explorer_surface())

    return combined or None


def after_model_callback(
    callback_context: CallbackContext | None,
    llm_response: LlmResponse,
    *,
    force_surface_builder: Any | None = None,
) -> LlmResponse | None:
    """Guardrail 10: Wrap A2UI surface emission in try/except so UI failures degrade gracefully to text."""
    try:
        content = getattr(llm_response, "content", None)
        if content is None or not getattr(content, "parts", None):
            return None

        # Skip intermediate tool-calling turns so surfaces attach only to final model responses
        if any(getattr(p, "function_call", None) is not None for p in (content.parts or [])):
            return None

        # Check if an A2UI Part is already attached
        for existing_part in content.parts or []:
            if (
                existing_part.inline_data
                and existing_part.inline_data.data
                and A2UI_OPEN_TAG
                in (
                    existing_part.inline_data.data
                    if isinstance(existing_part.inline_data.data, bytes)
                    else existing_part.inline_data.data.encode("utf-8")
                )
            ):
                return None

        combined_text = " ".join(p.text for p in (content.parts or []) if p.text)
        messages = (
            force_surface_builder()
            if callable(force_surface_builder)
            else _select_surface_for_text(combined_text)
        )
        if messages:
            a2ui_part = wrap_a2ui_part(messages)
            content.parts = list(content.parts) + [a2ui_part]
            return llm_response
    except Exception as exc:
        logger.warning(
            "A2UI v0.9 surface generation failed; degrading gracefully to prose text: %s",
            exc,
        )
    return None


class SafetyAndA2UIPlugin(BasePlugin):
    """ADK Plugin enforcing A2UI v0.9 history sanitization, 16KB tool budget, and safe UI emission."""

    def __init__(self, name: str = "safety_and_a2ui_plugin") -> None:
        super().__init__(name=name)

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> LlmResponse | None:
        return before_model_call(callback_context, llm_request)

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> LlmResponse | None:
        return after_model_callback(callback_context, llm_response)

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        if isinstance(result, dict):
            return enforce_tool_output_budget(result)
        return None


class BigQueryAgentAnalyticsPlugin(BasePlugin):
    """Hermetic-safe ADK BigQuery Agent Analytics Plugin wrapper for Gemini Enterprise telemetry."""

    def __init__(
        self,
        project_id: str,
        dataset_id: str = "sre_agent_analytics",
        table_id: str = "agent_events",
        location: str = "US",
        **kwargs: Any,
    ) -> None:
        super().__init__(name="bigquery_agent_analytics")
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.location = location
        self.extra_config = kwargs

    async def on_user_message_callback(
        self,
        *,
        invocation_context: Any,
        user_message: types.Content,
    ) -> types.Content | None:
        return None

# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""A2A v0.3 + A2UI v0.9 compatibility bridge for Google ADK and Gemini Enterprise."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.a2ui.primitives import A2UI_CLOSE_TAG, A2UI_MIME_TYPE, A2UI_OPEN_TAG

logger = logging.getLogger(__name__)

_BRIDGE_INSTALLED = False


def install_a2a_bridge() -> None:
    """Install the A2UI v0.9 DataPart & LongRunningTool compatibility bridge on google.adk.a2a."""
    global _BRIDGE_INSTALLED
    if _BRIDGE_INSTALLED:
        return

    try:
        from google.adk.a2a import _compat
        from google.adk.a2a.converters import event_converter, from_adk_event, part_converter
        from google.adk.a2a.executor import a2a_agent_executor
    except Exception as exc:  # pragma: no cover
        logger.debug("Skipping A2A bridge installation (a2a modules unavailable): %s", exc)
        return

    orig_part_converter = part_converter.convert_genai_part_to_a2a_part

    def a2ui_aware_part_converter(part: Any) -> Any:
        try:
            if (
                part is not None
                and getattr(part, "inline_data", None) is not None
                and getattr(part.inline_data, "data", None)
            ):
                raw_bytes = part.inline_data.data
                raw_text = (
                    raw_bytes.decode("utf-8", errors="ignore")
                    if isinstance(raw_bytes, (bytes, bytearray))
                    else str(raw_bytes)
                )
                open_tag = A2UI_OPEN_TAG.decode("utf-8")
                close_tag = A2UI_CLOSE_TAG.decode("utf-8")
                if raw_text.startswith(open_tag) and raw_text.endswith(close_tag):
                    inner_json = raw_text[len(open_tag) : -len(close_tag)]
                    parsed = json.loads(inner_json)
                    part_meta = dict(getattr(part, "part_metadata", None) or {})
                    if "mimeType" not in part_meta:
                        part_meta["mimeType"] = A2UI_MIME_TYPE
                    if isinstance(parsed, list):
                        return [
                            _compat.make_data_part(
                                data=item if isinstance(item, dict) else {"value": item},
                                metadata=dict(part_meta),
                            )
                            for item in parsed
                        ]
                    if isinstance(parsed, dict):
                        return _compat.make_data_part(data=parsed, metadata=dict(part_meta))
        except Exception as exc:  # pragma: no cover
            logger.warning("A2UI part conversion fallback due to error: %s", exc)

        return orig_part_converter(part)

    part_converter.convert_genai_part_to_a2a_part = a2ui_aware_part_converter
    event_converter.convert_genai_part_to_a2a_part = a2ui_aware_part_converter
    from_adk_event.convert_genai_part_to_a2a_part = a2ui_aware_part_converter

    orig_event_converter = event_converter.convert_event_to_a2a_events

    def a2ui_aware_event_converter(
        event: Any,
        invocation_context: Any,
        task_id: Any = None,
        context_id: Any = None,
        custom_part_converter: Any = a2ui_aware_part_converter,
    ) -> Any:
        if getattr(event, "long_running_tool_ids", None):
            event.long_running_tool_ids = set()
        return orig_event_converter(
            event,
            invocation_context,
            task_id,
            context_id,
            a2ui_aware_part_converter,
        )

    event_converter.convert_event_to_a2a_events = a2ui_aware_event_converter
    from_adk_event.convert_event_to_a2a_events = a2ui_aware_event_converter
    a2a_agent_executor.convert_event_to_a2a_events = a2ui_aware_event_converter

    try:
        cfg_fields = a2a_agent_executor.A2aAgentExecutorConfig.model_fields
        if "gen_ai_part_converter" in cfg_fields:
            cfg_fields["gen_ai_part_converter"].default = a2ui_aware_part_converter
        if "event_converter" in cfg_fields:
            cfg_fields["event_converter"].default = a2ui_aware_event_converter
        a2a_agent_executor.A2aAgentExecutorConfig.model_rebuild(force=True)
    except Exception as exc:  # pragma: no cover
        logger.debug("Could not rebuild A2aAgentExecutorConfig defaults: %s", exc)

    _BRIDGE_INSTALLED = True

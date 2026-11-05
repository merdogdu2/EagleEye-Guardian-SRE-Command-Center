# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""A2UI v0.9 primitives, raw DEFLATE URL-fragment codec, and 10-rule validator."""

from __future__ import annotations

import base64
import json
import math
import re
import zlib
from typing import Any

from google.genai.types import Blob, Part

A2UI_VERSION: str = "v0.9"
A2UI_CATALOG_ID: str = (
    "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"
)
A2UI_MIME_TYPE: str = "application/json+a2ui"
A2UI_OPEN_TAG: bytes = b"<a2a_datapart_json>"
A2UI_CLOSE_TAG: bytes = b"</a2a_datapart_json>"

ALLOWED_USAGE_HINTS: frozenset[str] = frozenset(
    {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "subtitle1",
        "subtitle2",
        "body1",
        "body2",
        "caption",
        "body",
    }
)
ALLOWED_ENVELOPE_VERBS: frozenset[str] = frozenset(
    {"createSurface", "updateDataModel", "updateComponents", "deleteSurface"}
)
_NUMERIC_LIKE_RE = re.compile(r"^[\$\€\£]?[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?$")


def coerce_clean_number(value: Any) -> int | float | str | bool | None:
    """Coerce cell value to clean int/float, stripping commas/currency and guarding NaN/inf."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return 0.0
        return round(value, 4)
    if isinstance(value, str):
        stripped = value.strip()
        if _NUMERIC_LIKE_RE.match(stripped):
            cleaned = re.sub(r"[\$\€\£,%]", "", stripped).replace(",", "")
            try:
                return float(cleaned) if "." in cleaned else int(cleaned)
            except ValueError:
                return value
    return value


def encode_state_fragment(state: dict[str, Any]) -> str:
    """Compress state JSON using RFC 1951 raw DEFLATE into 'z.<base64url>'."""
    raw_json = json.dumps(state, separators=(",", ":"), sort_keys=True).encode("utf-8")
    compressor = zlib.compressobj(level=9, wbits=-zlib.MAX_WBITS)
    compressed = compressor.compress(raw_json) + compressor.flush()
    b64 = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    return f"z.{b64}"


def decode_state_fragment(fragment: str) -> dict[str, Any]:
    """Decompress 'z.<base64url>' raw DEFLATE fragment back into a Python dictionary."""
    token = fragment.strip()
    if token.startswith("#s="):
        token = token[3:]
    elif token.startswith("s="):
        token = token[2:]
    if not token.startswith("z."):
        raise ValueError("Invalid state fragment prefix: expected 'z.<base64url>'")
    b64_payload = token[2:]
    padding = "=" * ((4 - len(b64_payload) % 4) % 4)
    compressed = base64.urlsafe_b64decode(b64_payload + padding)
    raw_json = zlib.decompress(compressed, wbits=-zlib.MAX_WBITS)
    parsed = json.loads(raw_json.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Decoded state fragment must be a JSON object")
    return parsed


def wrap_a2ui_part(messages: list[dict[str, Any]], *, validate: bool = True) -> Part:
    """Validate and wrap an A2UI v0.9 JSON envelope array inside a Gemini Enterprise Part."""
    if validate:
        errors = validate_a2ui_envelope(messages)
        if errors:
            raise ValueError(f"A2UI v0.9 validation failed: {'; '.join(errors)}")
    json_bytes = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Part(
        inline_data=Blob(
            mime_type="text/plain",
            data=A2UI_OPEN_TAG + json_bytes + A2UI_CLOSE_TAG,
        ),
        part_metadata={"mimeType": A2UI_MIME_TYPE},
    )


def extract_a2ui_messages_from_part(part: Part) -> list[dict[str, Any]] | None:
    """Extract the A2UI v0.9 JSON message array from a Part if present."""
    if part.inline_data and part.inline_data.data:
        raw = part.inline_data.data
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if A2UI_OPEN_TAG in raw and A2UI_CLOSE_TAG in raw:
            start = raw.index(A2UI_OPEN_TAG) + len(A2UI_OPEN_TAG)
            end = raw.index(A2UI_CLOSE_TAG)
            payload = json.loads(raw[start:end].decode("utf-8"))
            if isinstance(payload, list):
                return payload
    return None


def make_text(
    comp_id: str,
    text: str | dict[str, Any],
    usage_hint: str = "body1",
) -> dict[str, Any]:
    """Create a guardrail-compliant MaterialText component."""
    if usage_hint not in ALLOWED_USAGE_HINTS:
        raise ValueError(f"Forbidden usageHint '{usage_hint}'. Allowed: {sorted(ALLOWED_USAGE_HINTS)}")
    if isinstance(text, str) and text.lstrip().startswith("#"):
        text = text.lstrip("#").lstrip()
    return {
        "id": comp_id,
        "component": "MaterialText",
        "text": text,
        "usageHint": usage_hint,
    }


def make_formatted_number_text(
    comp_id: str,
    data_path: str,
    prefix: str = "",
    suffix: str = "",
    decimals: int = 0,
    usage_hint: str = "body1",
) -> dict[str, Any]:
    """Bind a numeric path inside MaterialText using formatNumber with returnType='string'."""
    if usage_hint not in ALLOWED_USAGE_HINTS:
        raise ValueError(f"Forbidden usageHint '{usage_hint}'.")
    return {
        "id": comp_id,
        "component": "MaterialText",
        "usageHint": usage_hint,
        "text": {
            "call": "formatNumber",
            "returnType": "string",
            "args": {
                "value": {"path": data_path},
                "decimals": decimals,
                "prefix": prefix,
                "suffix": suffix,
            },
        },
    }


def make_button(
    comp_id: str,
    label: str,
    event_name: str,
    prompt: str,
    extra_context: dict[str, Any] | None = None,
    variant: str = "filled",
) -> dict[str, Any]:
    """Create a MaterialButton with mandatory 'prompt' in action.event.context."""
    if not prompt or not prompt.strip():
        raise ValueError("Button action.event.context['prompt'] must be a non-empty string")
    context: dict[str, Any] = {"prompt": prompt.strip()}
    if extra_context:
        context.update(extra_context)
    return {
        "id": comp_id,
        "component": "MaterialButton",
        "label": label,
        "variant": variant,
        "action": {
            "event": {
                "name": event_name,
                "context": context,
            }
        },
    }


def validate_a2ui_envelope(messages: list[dict[str, Any]]) -> list[str]:
    """Validate an A2UI v0.9 JSON envelope array against all 10 mandatory guardrails."""
    errors: list[str] = []
    if not isinstance(messages, list) or not messages:
        return ["Envelope must be a non-empty JSON array of v0.9 verb objects."]

    data_model_by_surface: dict[str, dict[str, Any]] = {}

    for idx, item in enumerate(messages):
        if not isinstance(item, dict):
            errors.append(f"Envelope item[{idx}] must be a dict.")
            continue
        if item.get("version") != A2UI_VERSION:
            errors.append(f"Envelope item[{idx}] missing or invalid version (expected 'v0.9').")
        present_verbs = [k for k in item if k != "version"]
        if len(present_verbs) != 1 or present_verbs[0] not in ALLOWED_ENVELOPE_VERBS:
            errors.append(
                f"Envelope item[{idx}] must contain exactly one verb from {sorted(ALLOWED_ENVELOPE_VERBS)}."
            )
            continue

        verb = present_verbs[0]
        body = item[verb]
        if not isinstance(body, dict):
            errors.append(f"Envelope item[{idx}].{verb} must be an object.")
            continue

        surface_id = body.get("surfaceId")
        if not isinstance(surface_id, str) or not surface_id.strip():
            errors.append(f"Envelope item[{idx}].{verb} missing non-empty surfaceId.")

        if verb == "createSurface":
            if body.get("catalogId") != A2UI_CATALOG_ID:
                errors.append(
                    f"createSurface[{surface_id}] catalogId must equal '{A2UI_CATALOG_ID}'."
                )

        elif verb == "updateDataModel":
            value = body.get("value")
            if isinstance(surface_id, str) and isinstance(value, dict):
                data_model_by_surface.setdefault(surface_id, {}).update(value)
                # Guardrail 4 check on RichTable data inside updateDataModel
                for dm_key, dm_val in value.items():
                    if isinstance(dm_val, dict) and "columns" in dm_val and "rows" in dm_val:
                        if dm_val.get("spec") != {}:
                            errors.append(
                                f"Rule 4 violation: RichTable data model '{dm_key}' must have spec={{}}."
                            )
                        for r_idx, row in enumerate(dm_val.get("rows", [])):
                            if isinstance(row, dict):
                                for col_k, cell_v in row.items():
                                    if isinstance(cell_v, float) and (
                                        math.isnan(cell_v) or math.isinf(cell_v)
                                    ):
                                        errors.append(
                                            f"Rule 4 violation: RichTable row[{r_idx}].{col_k} contains NaN/inf."
                                        )
                                    elif isinstance(cell_v, str) and _NUMERIC_LIKE_RE.match(
                                        cell_v.strip()
                                    ):
                                        errors.append(
                                            f"Rule 4 violation: RichTable row[{r_idx}].{col_k} has formatted numeric string '{cell_v}'."
                                        )

        elif verb == "updateComponents":
            components = body.get("components")
            if not isinstance(components, list) or not components:
                errors.append(f"Rule 5 violation: updateComponents[{surface_id}] must be a non-empty list.")
                continue

            comp_by_id: dict[str, dict[str, Any]] = {}
            for c_idx, comp in enumerate(components):
                if not isinstance(comp, dict):
                    errors.append(f"Component[{c_idx}] in {surface_id} must be a dict.")
                    continue
                cid = comp.get("id")
                ctype = comp.get("component")
                if not isinstance(cid, str) or not cid:
                    errors.append(f"Rule 5 violation: Component[{c_idx}] missing string 'id'.")
                    continue
                comp_by_id[cid] = comp

                # Rule 5: children must be flat string ID list
                if "children" in comp:
                    ch = comp["children"]
                    if not isinstance(ch, list) or not all(isinstance(x, str) for x in ch):
                        errors.append(
                            f"Rule 5 violation: Component '{cid}' children must be a list of string IDs."
                        )

                # Rule 1 & Rule 2 & Rule 7: MaterialText checks
                if ctype == "MaterialText":
                    hint = comp.get("usageHint")
                    if hint is not None and hint not in ALLOWED_USAGE_HINTS:
                        errors.append(
                            f"Rule 1 violation: MaterialText '{cid}' uses forbidden usageHint '{hint}'."
                        )
                    txt = comp.get("text")
                    if hint is not None and isinstance(txt, str) and txt.lstrip().startswith("#"):
                        errors.append(
                            f"Rule 2 violation: MaterialText '{cid}' uses Markdown '#' heading with usageHint='{hint}'."
                        )
                    if isinstance(txt, dict):
                        if "path" in txt and "call" not in txt:
                            errors.append(
                                f"Rule 7 violation: MaterialText '{cid}' binds raw path without formatNumber/formatString."
                            )
                        if "call" in txt and txt.get("returnType") != "string":
                            errors.append(
                                f"Rule 7 violation: MaterialText '{cid}' call '{txt.get('call')}' must set returnType='string'."
                            )

                # Rule 6: VegaChart & RichTable complex object binding
                if ctype == "VegaChart":
                    spec_binding = comp.get("spec")
                    if not isinstance(spec_binding, dict) or not str(
                        spec_binding.get("path", "")
                    ).startswith("/"):
                        errors.append(
                            f"Rule 6 violation: VegaChart '{cid}' spec must bind via {{'path': '/...'}}."
                        )

                if ctype == "RichTable":
                    td_binding = comp.get("tableData")
                    if not isinstance(td_binding, dict) or not str(
                        td_binding.get("path", "")
                    ).startswith("/"):
                        errors.append(
                            f"Rule 6 violation: RichTable '{cid}' tableData must bind via {{'path': '/...'}}."
                        )

                # Rule 8: MaterialButton action.event.context.prompt
                if ctype == "MaterialButton":
                    action = comp.get("action")
                    if isinstance(action, dict):
                        event = action.get("event", {})
                        ctx = event.get("context", {}) if isinstance(event, dict) else {}
                        prompt = ctx.get("prompt") if isinstance(ctx, dict) else None
                        if not isinstance(prompt, str) or not prompt.strip():
                            errors.append(
                                f"Rule 8 violation: MaterialButton '{cid}' missing non-empty action.event.context.prompt."
                            )

            # Rule 5: Must have "id": "root"
            if "root" not in comp_by_id:
                errors.append(
                    f"Rule 5 violation: updateComponents[{surface_id}] missing entry point component with id='root'."
                )
            else:
                root_comp = comp_by_id["root"]
                # Rule 3: Canvas root must wrap content in a single top-level MaterialColumn with justify="start"
                if root_comp.get("component") == "Canvas":
                    root_children = root_comp.get("children", [])
                    if not isinstance(root_children, list) or len(root_children) != 1:
                        errors.append(
                            f"Rule 3 violation: Canvas root in '{surface_id}' must have exactly 1 direct child."
                        )
                    else:
                        first_child = comp_by_id.get(root_children[0])
                        if (
                            not first_child
                            or first_child.get("component") != "MaterialColumn"
                            or first_child.get("justify") != "start"
                        ):
                            errors.append(
                                f"Rule 3 violation: Canvas root child in '{surface_id}' must be a MaterialColumn with justify='start'."
                            )

    return errors

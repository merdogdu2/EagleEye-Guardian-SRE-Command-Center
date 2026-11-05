# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for A2UI v0.9 surfaces, 10 guardrails, and #s=z.<deflate-raw-base64url> codec."""

from __future__ import annotations

import pytest

from app.core.a2ui.primitives import (
    A2UI_CATALOG_ID,
    A2UI_MIME_TYPE,
    decode_state_fragment,
    encode_state_fragment,
    extract_a2ui_messages_from_part,
    validate_a2ui_envelope,
    wrap_a2ui_part,
)
from app.core.a2ui.surfaces import (
    build_all_reference_surfaces,
    build_sre_command_center_iframe_surface,
)


def test_all_reference_surfaces_pass_10_guardrails() -> None:
    """Verify every built-in A2UI v0.9 surface passes all 10 mandatory guardrails."""
    surfaces = build_all_reference_surfaces()
    assert len(surfaces) == 5
    for name, messages in surfaces.items():
        errors = validate_a2ui_envelope(messages)
        assert not errors, f"Surface {name} failed A2UI v0.9 validation: {errors}"
        part = wrap_a2ui_part(messages)
        assert part.part_metadata == {"mimeType": A2UI_MIME_TYPE}
        extracted = extract_a2ui_messages_from_part(part)
        assert extracted == messages


def test_deflate_raw_url_fragment_round_trip() -> None:
    """Verify #s=z.<base64url> raw DEFLATE compression and decompression round-trip."""
    sample_state = {
        "activeTab": "hyperdisk",
        "region": "europe-west2",
        "capacityTib": 64,
        "iops": 640000,
        "throughputMib": 20000,
        "tornWriteProtection": True,
        "regions": ["europe-west2", "us-east1", "australia-southeast1"],
    }
    fragment = encode_state_fragment(sample_state)
    assert fragment.startswith("z.")
    assert "=" not in fragment

    decoded = decode_state_fragment(fragment)
    assert decoded == sample_state

    # Also test with '#s=' prefix as present in browser window.location.hash
    decoded_hash = decode_state_fragment(f"#s={fragment}")
    assert decoded_hash == sample_state


def test_iframe_surface_embeds_origin_and_compressed_state() -> None:
    """Verify the SRE Command Center Canvas surface embeds origin=REPLACE_WITH_PARENT_ORIGIN#s=z."""
    messages = build_sre_command_center_iframe_surface(active_tab="spanner")
    comp_msg = next(m["updateComponents"] for m in messages if "updateComponents" in m)
    iframe_comp = next(c for c in comp_msg["components"] if c["component"] == "IFrameUrl")
    url = iframe_comp["url"]
    assert "origin=REPLACE_WITH_PARENT_ORIGIN#s=z." in url
    fragment = url.split("#s=", 1)[1]
    decoded = decode_state_fragment(fragment)
    assert decoded["activeTab"] == "spanner"


def test_validator_catches_all_guardrail_violations() -> None:
    """Verify validate_a2ui_envelope catches violations of Rules 1 through 8."""
    invalid_envelope = [
        {
            "version": "v0.9",
            "createSurface": {
                "surfaceId": "bad-surface",
                "catalogId": A2UI_CATALOG_ID,
            },
        },
        {
            "version": "v0.9",
            "updateDataModel": {
                "surfaceId": "bad-surface",
                "value": {
                    "badTable": {
                        "spec": {"invalidNonEmpty": True},
                        "columns": [{"id": "cost", "label": "Cost"}],
                        "rows": [{"cost": "$12,345.00"}],
                    }
                },
            },
        },
        {
            "version": "v0.9",
            "updateComponents": {
                "surfaceId": "bad-surface",
                "components": [
                    {
                        "id": "root",
                        "component": "Canvas",
                        "children": ["text-h6", "chart-inline"],
                    },
                    {
                        "id": "text-h6",
                        "component": "MaterialText",
                        "text": "# Markdown Heading",
                        "usageHint": "h6",
                    },
                    {
                        "id": "text-raw-num",
                        "component": "MaterialText",
                        "text": {"path": "/rawNumber"},
                        "usageHint": "body1",
                    },
                    {
                        "id": "chart-inline",
                        "component": "VegaChart",
                        "spec": {"mark": "bar"},
                    },
                    {
                        "id": "btn-no-prompt",
                        "component": "MaterialButton",
                        "label": "Click",
                        "action": {"event": {"name": "do_something", "context": {}}},
                    },
                ],
            },
        },
    ]

    errors = validate_a2ui_envelope(invalid_envelope)
    joined = "\n".join(errors)
    assert "Rule 1 violation" in joined
    assert "Rule 2 violation" in joined
    assert "Rule 3 violation" in joined
    assert "Rule 4 violation" in joined
    assert "Rule 6 violation" in joined
    assert "Rule 7 violation" in joined
    assert "Rule 8 violation" in joined

    with pytest.raises(ValueError, match="A2UI v0.9 validation failed"):
        wrap_a2ui_part(invalid_envelope)


def test_a2a_endpoint_and_a2ui_datapart_conversion() -> None:
    """Verify /a2a/app/.well-known/agent-card.json and POST /a2a/app emit A2UI v0.9 DataParts."""
    from fastapi.testclient import TestClient

    from app.server import A2UI_EXTENSION_URI, app

    with TestClient(app) as client:
        card_resp = client.get("/a2a/app/.well-known/agent-card.json")
        assert card_resp.status_code == 200
        card = card_resp.json()
        assert card["name"] == "eagleeye_guardian_sre"
        ext_uris = [e["uri"] for e in card.get("capabilities", {}).get("extensions", [])]
        assert A2UI_EXTENSION_URI in ext_uris

        rpc_payload = {
            "jsonrpc": "2.0",
            "id": "test-a2ui-rpc-1",
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": "msg-a2ui-1",
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": "Scale Regional Hyperdisk Balanced HA in europe-west2 to 320,000 IOPS and 12,000 MiB/s.",
                        }
                    ],
                }
            },
        }
        rpc_resp = client.post(
            "/a2a/app",
            json=rpc_payload,
            headers={"X-A2A-Extensions": A2UI_EXTENSION_URI},
        )
        assert rpc_resp.status_code == 200
        assert A2UI_EXTENSION_URI in rpc_resp.headers.get("x-a2a-extensions", "")
        result = rpc_resp.json().get("result", {})
        artifacts = result.get("artifacts", [])
        assert artifacts, f"Expected A2A artifacts in response, got: {rpc_resp.json()}"
        all_parts = [p for art in artifacts for p in art.get("parts", [])]
        data_parts = [p for p in all_parts if p.get("kind") == "data"]
        assert len(data_parts) == 3
        assert data_parts[0]["metadata"]["mimeType"] == A2UI_MIME_TYPE
        assert "createSurface" in data_parts[0]["data"]
        assert "updateDataModel" in data_parts[1]["data"]
        assert "updateComponents" in data_parts[2]["data"]

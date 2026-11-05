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

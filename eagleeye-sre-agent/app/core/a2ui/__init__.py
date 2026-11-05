# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""A2UI v0.9 wire protocol primitives, surface builders, and action handlers."""

from app.core.a2ui.actions import dispatch_a2ui_action, parse_inbound_a2ui_action
from app.core.a2ui.primitives import (
    A2UI_CATALOG_ID,
    A2UI_MIME_TYPE,
    A2UI_VERSION,
    ALLOWED_USAGE_HINTS,
    decode_state_fragment,
    encode_state_fragment,
    extract_a2ui_messages_from_part,
    validate_a2ui_envelope,
    wrap_a2ui_part,
)
from app.core.a2ui.surfaces import (
    build_all_reference_surfaces,
    build_fleet_finops_explorer_surface,
    build_hitl_confirmation_surface,
    build_hitl_receipt_update_surface,
    build_incident_triage_surface,
    build_sre_command_center_iframe_surface,
)

__all__ = [
    "A2UI_CATALOG_ID",
    "A2UI_MIME_TYPE",
    "A2UI_VERSION",
    "ALLOWED_USAGE_HINTS",
    "build_all_reference_surfaces",
    "build_fleet_finops_explorer_surface",
    "build_hitl_confirmation_surface",
    "build_hitl_receipt_update_surface",
    "build_incident_triage_surface",
    "build_sre_command_center_iframe_surface",
    "decode_state_fragment",
    "dispatch_a2ui_action",
    "encode_state_fragment",
    "extract_a2ui_messages_from_part",
    "parse_inbound_a2ui_action",
    "validate_a2ui_envelope",
    "wrap_a2ui_part",
]

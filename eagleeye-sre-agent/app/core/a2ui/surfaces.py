# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Builders for the required EagleEye Guardian A2UI v0.9 surfaces."""

from __future__ import annotations

from typing import Any

from app.core.a2ui.primitives import (
    A2UI_CATALOG_ID,
    A2UI_VERSION,
    coerce_clean_number,
    encode_state_fragment,
    make_button,
    make_formatted_number_text,
    make_text,
)
from app.core.config import settings


def build_incident_triage_surface(
    incident_id: str = "INC-2026-8841",
    region: str = "europe-west2",
    exhausted_zone: str = "europe-west2-b",
    p99_latency_ms: float = 682.4,
    active_step_index: int = 1,
    surface_id: str = "sre-incident-triage-card",
) -> list[dict[str, Any]]:
    """Build the Inline Incident & SLO Triage Card (MaterialCard root)."""
    vega_spec: dict[str, Any] = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "POS Coupon API p99 Latency (ms) vs. Zonal Disk IOPS Saturation",
        "data": {
            "values": [
                {"time": "08:30", "p99_ms": 148, "iops_k": 58},
                {"time": "08:35", "p99_ms": 182, "iops_k": 76},
                {"time": "08:40", "p99_ms": 395, "iops_k": 98},
                {"time": "08:45", "p99_ms": 682, "iops_k": 100},
                {"time": "08:50", "p99_ms": 210, "iops_k": 320},
            ]
        },
        "mark": {"type": "line", "point": True},
        "encoding": {
            "x": {"field": "time", "type": "ordinal", "title": "UTC Timestamp"},
            "y": {"field": "p99_ms", "type": "quantitative", "title": "POS p99 Latency (ms)"},
            "tooltip": [
                {"field": "time", "type": "ordinal"},
                {"field": "p99_ms", "type": "quantitative"},
                {"field": "iops_k", "type": "quantitative"},
            ],
        },
    }

    step_titles = ["Detected", "Correlated", "Mitigating", "Resolved"]
    stepper_steps = [
        {
            "title": title,
            "status": (
                "completed"
                if idx < active_step_index or active_step_index >= len(step_titles) - 1
                else ("in_progress" if idx == active_step_index else "pending")
            ),
        }
        for idx, title in enumerate(step_titles)
    ]

    components: list[dict[str, Any]] = [
        {
            "id": "root",
            "component": "MaterialCard",
            "appearance": "raised",
            "children": ["card-col"],
        },
        {
            "id": "card-col",
            "component": "MaterialColumn",
            "justify": "start",
            "align": "stretch",
            "children": [
                "title-text",
                "subtitle-text",
                "p99-metric-text",
                "incident-stepper",
                "latency-vega-chart",
                "action-row",
            ],
        },
        make_text(
            "title-text",
            f"Incident {incident_id}: Retail POS Coupon SLA Breach ({region})",
            usage_hint="h4",
        ),
        make_text(
            "subtitle-text",
            f"Correlated ZONE_RESOURCE_POOL_EXHAUSTED in {exhausted_zone} + MySQL Zonal SSD PD 100k IOPS ceiling.",
            usage_hint="subtitle2",
        ),
        make_formatted_number_text(
            "p99-metric-text",
            data_path="/metrics/p99LatencyMs",
            prefix="Observed POS p99 Latency: ",
            suffix=" ms (SLA < 250 ms)",
            decimals=1,
            usage_hint="body1",
        ),
        {
            "id": "incident-stepper",
            "component": "Stepper",
            "activeStep": active_step_index,
            "steps": stepper_steps,
        },
        {
            "id": "latency-vega-chart",
            "component": "VegaChart",
            "spec": {"path": "/chartSpec"},
        },
        {
            "id": "action-row",
            "component": "MaterialRow",
            "children": [
                "btn-scale-iops",
                "btn-drain-zone",
                "btn-jira-incident",
                "btn-draft-postmortem",
            ],
        },
        make_button(
            "btn-scale-iops",
            "Scale Hyperdisk IOPS",
            "scale_hyperdisk_iops",
            f"Scale Regional Hyperdisk Balanced HA in {region} to 320,000 IOPS and 12,000 MiB/s for {incident_id}.",
            extra_context={
                "incidentId": incident_id,
                "region": region,
                "targetIops": 320000,
                "targetThroughputMib": 12000,
            },
        ),
        make_button(
            "btn-drain-zone",
            "Drain Zone",
            "drain_exhausted_zone",
            f"Drain POS traffic from exhausted zone {exhausted_zone} and shift to C4/N4 pools in {region}.",
            extra_context={"incidentId": incident_id, "region": region, "zone": exhausted_zone},
            variant="outlined",
        ),
        make_button(
            "btn-jira-incident",
            "Create Jira Incident",
            "create_jira_incident",
            f"Create P1 Jira incident via Atlassian Rovo for {incident_id} in {region} linked to Confluence runbook.",
            extra_context={"incidentId": incident_id, "region": region, "priority": "P1"},
            variant="outlined",
        ),
        make_button(
            "btn-draft-postmortem",
            "Draft Postmortem",
            "draft_workspace_postmortem",
            f"Generate a blameless postmortem Doc, executive Slides deck, and SLA timeline Sheet for {incident_id}.",
            extra_context={"incidentId": incident_id, "region": region},
            variant="tonal",
        ),
    ]

    return [
        {
            "version": A2UI_VERSION,
            "createSurface": {
                "surfaceId": surface_id,
                "catalogId": A2UI_CATALOG_ID,
            },
        },
        {
            "version": A2UI_VERSION,
            "updateDataModel": {
                "surfaceId": surface_id,
                "value": {
                    "chartSpec": vega_spec,
                    "metrics": {
                        "p99LatencyMs": coerce_clean_number(p99_latency_ms),
                    },
                },
            },
        },
        {
            "version": A2UI_VERSION,
            "updateComponents": {
                "surfaceId": surface_id,
                "components": components,
            },
        },
    ]


def build_hitl_confirmation_surface(
    action_id: str = "ACT-HD-SCALE-320K",
    target_disk: str = "loyalty-mysql-prod-eu-west2-hd-ha",
    target_region: str = "europe-west2",
    requested_iops: int = 320000,
    requested_throughput_mib: int = 12000,
    surface_id: str = "sre-hitl-confirmation-gate",
) -> list[dict[str, Any]]:
    """Build Inline Human-in-the-Loop (HITL) Confirmation Gate (MaterialCard root)."""
    components: list[dict[str, Any]] = [
        {
            "id": "root",
            "component": "MaterialCard",
            "appearance": "outlined",
            "children": ["gate-col"],
        },
        {
            "id": "gate-col",
            "component": "MaterialColumn",
            "justify": "start",
            "children": [
                "gate-title",
                "gate-subtitle",
                "select-tier",
                "input-iops",
                "input-change-reason",
                "gate-btn-row",
            ],
        },
        make_text(
            "gate-title",
            f"Human-in-the-Loop Approval Required ({action_id})",
            usage_hint="h4",
        ),
        make_text(
            "gate-subtitle",
            f"Confirm mutating infrastructure modification on {target_disk} ({target_region}). Note: Hyperdisk Dynamic Scaling allows 1 modification per 4-hour window.",
            usage_hint="body2",
        ),
        {
            "id": "select-tier",
            "component": "MaterialSelect",
            "label": "Target Storage Availability Tier",
            "value": {"path": "/form/storageTier"},
            "options": [
                {
                    "label": "Regional Hyperdisk Balanced HA (RPO=0, <2.5m RTO, Torn-Write Off)",
                    "value": "hyperdisk-balanced-high-availability",
                },
                {
                    "label": "Regional Hyperdisk Balanced Standard",
                    "value": "hyperdisk-balanced",
                },
            ],
            "checks": [
                {
                    "condition": {
                        "call": "required",
                        "args": {"value": {"path": "/form/storageTier"}},
                        "returnType": "boolean",
                    },
                    "message": "Storage tier selection is mandatory.",
                }
            ],
        },
        {
            "id": "input-iops",
            "component": "MaterialInput",
            "label": "Provisioned IOPS (Max 640,000)",
            "value": {"path": "/form/provisionedIops"},
            "checks": [
                {
                    "condition": {
                        "call": "required",
                        "args": {"value": {"path": "/form/provisionedIops"}},
                        "returnType": "boolean",
                    },
                    "message": "IOPS value is required.",
                },
                {
                    "condition": {
                        "call": "numeric",
                        "args": {
                            "value": {"path": "/form/provisionedIops"},
                            "min": 10000,
                            "max": 640000,
                        },
                        "returnType": "boolean",
                    },
                    "message": "IOPS must be between 10,000 and 640,000.",
                },
            ],
        },
        {
            "id": "input-change-reason",
            "component": "MaterialInput",
            "label": "Authorized Change Justification / Ticket ID",
            "value": {"path": "/form/justification"},
            "checks": [
                {
                    "condition": {
                        "call": "length",
                        "args": {
                            "value": {"path": "/form/justification"},
                            "min": 5,
                        },
                        "returnType": "boolean",
                    },
                    "message": "Provide a valid Jira ticket or justification.",
                }
            ],
        },
        {
            "id": "gate-btn-row",
            "component": "MaterialRow",
            "children": ["btn-confirm-hitl", "btn-cancel-hitl"],
        },
        make_button(
            "btn-confirm-hitl",
            "Confirm & Execute Change",
            "confirm_hitl_execution",
            f"Approve and execute {action_id} on {target_disk}: scale to {requested_iops} IOPS and {requested_throughput_mib} MiB/s.",
            extra_context={
                "surfaceId": surface_id,
                "actionId": action_id,
                "targetDisk": target_disk,
                "region": target_region,
                "requestedIops": requested_iops,
                "requestedThroughputMib": requested_throughput_mib,
            },
        ),
        make_button(
            "btn-cancel-hitl",
            "Cancel Change",
            "cancel_hitl_execution",
            f"Cancel infrastructure modification {action_id} on {target_disk}.",
            extra_context={
                "surfaceId": surface_id,
                "actionId": action_id,
                "targetDisk": target_disk,
            },
            variant="outlined",
        ),
    ]

    return [
        {
            "version": A2UI_VERSION,
            "createSurface": {
                "surfaceId": surface_id,
                "catalogId": A2UI_CATALOG_ID,
            },
        },
        {
            "version": A2UI_VERSION,
            "updateDataModel": {
                "surfaceId": surface_id,
                "value": {
                    "form": {
                        "storageTier": "hyperdisk-balanced-high-availability",
                        "provisionedIops": str(requested_iops),
                        "justification": "INC-2026-8841 POS SLA Mitigation",
                    }
                },
            },
        },
        {
            "version": A2UI_VERSION,
            "updateComponents": {
                "surfaceId": surface_id,
                "components": components,
            },
        },
    ]


def build_hitl_receipt_update_surface(
    action_id: str = "ACT-HD-SCALE-320K",
    target_disk: str = "loyalty-mysql-prod-eu-west2-hd-ha",
    status: str = "EXECUTED",
    summary: str = "Scaled Regional Hyperdisk Balanced HA to 320,000 IOPS / 12,000 MiB/s (RPO=0, Torn-Write Protection active, next scaling window unlocked in 4h).",
    surface_id: str = "sre-hitl-confirmation-gate",
    include_create_surface: bool = False,
) -> list[dict[str, Any]]:
    """Update the HITL Confirmation Gate in-place (same surfaceId) with a read-only execution receipt."""
    components: list[dict[str, Any]] = [
        {
            "id": "root",
            "component": "MaterialCard",
            "appearance": "raised",
            "children": ["receipt-col"],
        },
        {
            "id": "receipt-col",
            "component": "MaterialColumn",
            "justify": "start",
            "children": ["receipt-title", "receipt-target", "receipt-summary"],
        },
        make_text(
            "receipt-title",
            f"Execution Receipt [{status}] — {action_id}",
            usage_hint="h4",
        ),
        make_text(
            "receipt-target",
            f"Target Resource: {target_disk}",
            usage_hint="subtitle2",
        ),
        make_text(
            "receipt-summary",
            summary,
            usage_hint="body1",
        ),
    ]
    messages: list[dict[str, Any]] = []
    if include_create_surface:
        messages.append(
            {
                "version": A2UI_VERSION,
                "createSurface": {
                    "surfaceId": surface_id,
                    "catalogId": A2UI_CATALOG_ID,
                },
            }
        )
    messages.append(
        {
            "version": A2UI_VERSION,
            "updateComponents": {
                "surfaceId": surface_id,
                "components": components,
            },
        }
    )
    return messages


def build_fleet_finops_explorer_surface(
    rows: list[dict[str, Any]] | None = None,
    surface_id: str = "sre-fleet-finops-explorer",
) -> list[dict[str, Any]]:
    """Build Native Side-Panel Fleet & FinOps Explorer (Canvas root + Looker Studio RichTable)."""
    default_rows: list[dict[str, Any]] = rows or [
        {
            "region": "europe-west2",
            "legacy_n1_vms": 42,
            "modern_c4_n4_vms": 180,
            "idle_standby_vms": 16,
            "current_iops": 100000,
            "target_hd_ha_iops": 640000,
            "monthly_net_savings_usd": 48250.0,
        },
        {
            "region": "europe-west1",
            "legacy_n1_vms": 18,
            "modern_c4_n4_vms": 140,
            "idle_standby_vms": 12,
            "current_iops": 100000,
            "target_hd_ha_iops": 480000,
            "monthly_net_savings_usd": 34900.0,
        },
        {
            "region": "us-east1",
            "legacy_n1_vms": 55,
            "modern_c4_n4_vms": 220,
            "idle_standby_vms": 20,
            "current_iops": 100000,
            "target_hd_ha_iops": 640000,
            "monthly_net_savings_usd": 61400.0,
        },
        {
            "region": "us-east4",
            "legacy_n1_vms": 12,
            "modern_c4_n4_vms": 160,
            "idle_standby_vms": 8,
            "current_iops": 100000,
            "target_hd_ha_iops": 360000,
            "monthly_net_savings_usd": 22800.0,
        },
        {
            "region": "australia-southeast1",
            "legacy_n1_vms": 24,
            "modern_c4_n4_vms": 96,
            "idle_standby_vms": 10,
            "current_iops": 100000,
            "target_hd_ha_iops": 320000,
            "monthly_net_savings_usd": 29150.0,
        },
        {
            "region": "australia-southeast2",
            "legacy_n1_vms": 8,
            "modern_c4_n4_vms": 74,
            "idle_standby_vms": 6,
            "current_iops": 100000,
            "target_hd_ha_iops": 320000,
            "monthly_net_savings_usd": 17600.0,
        },
    ]

    sanitized_rows = [
        {k: coerce_clean_number(v) for k, v in row.items()} for row in default_rows
    ]
    total_monthly_savings = sum(
        float(r.get("monthly_net_savings_usd", 0.0)) for r in sanitized_rows
    )

    table_data: dict[str, Any] = {
        "spec": {},
        "columns": [
            {"id": "region", "label": "Retail Region", "type": "string"},
            {"id": "legacy_n1_vms", "label": "Legacy N1 VMs", "type": "number"},
            {"id": "modern_c4_n4_vms", "label": "Gen 3/4 (C4/N4/C3) VMs", "type": "number"},
            {"id": "idle_standby_vms", "label": "Idle Standby VMs to Retire", "type": "number"},
            {"id": "current_iops", "label": "Zonal SSD PD IOPS Cap", "type": "number"},
            {"id": "target_hd_ha_iops", "label": "Hyperdisk Balanced HA IOPS", "type": "number"},
            {
                "id": "monthly_net_savings_usd",
                "label": "Monthly Net FinOps Savings (USD)",
                "type": "number",
            },
        ],
        "rows": sanitized_rows,
    }

    components: list[dict[str, Any]] = [
        {
            "id": "root",
            "component": "Canvas",
            "children": ["canvas-main-col"],
            "autoOpen": True,
            "cardTitle": "Global Retail Fleet & FinOps Explorer",
            "cardDescription": "Multi-region N1 exit, Idle Standby VM retirement & Hyperdisk Balanced HA metrics",
            "cardIcon": "table_chart",
        },
        {
            "id": "canvas-main-col",
            "component": "MaterialColumn",
            "justify": "start",
            "children": [
                "explorer-title",
                "explorer-subtitle",
                "explorer-savings-summary",
                "fleet-rich-table",
                "explorer-actions",
            ],
        },
        make_text(
            "explorer-title",
            "Global Retail Fleet, N1 Exit & Hyperdisk Balanced HA FinOps Explorer",
            usage_hint="h3",
        ),
        make_text(
            "explorer-subtitle",
            "Multi-region Compute Engine C4/N4 modernization, Idle Standby Reservation retirement, and Regional Hyperdisk Balanced HA (RPO=0) posture.",
            usage_hint="body2",
        ),
        make_formatted_number_text(
            "explorer-savings-summary",
            data_path="/summary/totalMonthlySavingsUsd",
            prefix="Projected Fleet Monthly Net FinOps Savings: $",
            suffix=" USD / month",
            decimals=2,
            usage_hint="subtitle1",
        ),
        {
            "id": "fleet-rich-table",
            "component": "RichTable",
            "tableData": {"path": "/fleetTableData"},
        },
        {
            "id": "explorer-actions",
            "component": "MaterialRow",
            "children": ["btn-open-workbench", "btn-retire-idle-reservations"],
        },
        make_button(
            "btn-open-workbench",
            "Open Interactive SRE Command Center",
            "open_sre_command_center",
            "Open the interactive EagleEye SRE Command Center workbench in the side-panel Canvas.",
            extra_context={"activeTab": "capacity"},
        ),
        make_button(
            "btn-retire-idle-reservations",
            "Stage Idle Reservation Retirement",
            "stage_idle_reservation_retirement",
            "Stage retirement of 72 idle warm-standby VMs replaced by Regional Hyperdisk Balanced HA synchronous replication.",
            extra_context={"retiredVmCount": 72},
            variant="outlined",
        ),
    ]

    return [
        {
            "version": A2UI_VERSION,
            "createSurface": {
                "surfaceId": surface_id,
                "catalogId": A2UI_CATALOG_ID,
            },
        },
        {
            "version": A2UI_VERSION,
            "updateDataModel": {
                "surfaceId": surface_id,
                "value": {
                    "fleetTableData": table_data,
                    "summary": {
                        "totalMonthlySavingsUsd": coerce_clean_number(total_monthly_savings),
                    },
                },
            },
        },
        {
            "version": A2UI_VERSION,
            "updateComponents": {
                "surfaceId": surface_id,
                "components": components,
            },
        },
    ]


def build_sre_command_center_iframe_surface(
    active_tab: str = "capacity",
    state_payload: dict[str, Any] | None = None,
    surface_id: str = "sre-command-center-canvas",
) -> list[dict[str, Any]]:
    """Build Custom Side-Panel SRE Command Center (Canvas root + IFrameUrl with #s=z.<base64url>)."""
    payload: dict[str, Any] = state_payload or {
        "activeTab": active_tab,
        "slaTargetMs": settings.pos_p99_sla_ms,
        "regions": list(settings.retail_regions),
        "incident": {
            "id": "INC-2026-8841",
            "region": "europe-west2",
            "zone": "europe-west2-b",
            "p99Ms": 682.4,
            "status": "Correlated",
        },
        "hyperdiskDefaults": {
            "capacityTib": 64,
            "iops": 320000,
            "throughputMib": 12000,
            "discountPct": 28,
            "retiredStandbyVms": 16,
            "tornWriteProtection": True,
        },
        "gpuAdvisor": {
            "accelerator": "NVIDIA RTX PRO 6000 (G4)",
            "machineType": "g4-standard-384",
            "recommendedModel": "DWS_FLEX_START",
        },
    }
    compressed_fragment = encode_state_fragment(payload)
    base_url = settings.iframe_base_url.rstrip("/")
    iframe_url = f"{base_url}/?origin=REPLACE_WITH_PARENT_ORIGIN#s={compressed_fragment}"

    components: list[dict[str, Any]] = [
        {
            "id": "root",
            "component": "Canvas",
            "children": ["iframe-canvas-col"],
            "autoOpen": True,
            "cardTitle": "EagleEye Guardian SRE Command Center",
            "cardDescription": "Interactive 4-Tab Capacity, Hyperdisk HA FinOps, Spanner & VPC-SC Workbench",
            "cardIcon": "dashboard_customize",
        },
        {
            "id": "iframe-canvas-col",
            "component": "MaterialColumn",
            "justify": "start",
            "children": [
                "iframe-header",
                "iframe-caption",
                "sre-workbench-iframe",
            ],
        },
        make_text(
            "iframe-header",
            "EagleEye Guardian — Stateless SRE Command Center Workbench",
            usage_hint="h3",
        ),
        make_text(
            "iframe-caption",
            "Zero-privilege URL-hash DEFLATE hydration (#s=z.*) with bidirectional a2ui_action bridge.",
            usage_hint="caption",
        ),
        {
            "id": "sre-workbench-iframe",
            "component": "IFrameUrl",
            "url": iframe_url,
            "title": "EagleEye Guardian SRE Command Center",
            "height": 780,
        },
    ]

    return [
        {
            "version": A2UI_VERSION,
            "createSurface": {
                "surfaceId": surface_id,
                "catalogId": A2UI_CATALOG_ID,
            },
        },
        {
            "version": A2UI_VERSION,
            "updateDataModel": {
                "surfaceId": surface_id,
                "value": {
                    "workbenchMeta": {
                        "activeTab": active_tab,
                        "fragmentLength": len(compressed_fragment),
                    }
                },
            },
        },
        {
            "version": A2UI_VERSION,
            "updateComponents": {
                "surfaceId": surface_id,
                "components": components,
            },
        },
    ]


def build_all_reference_surfaces() -> dict[str, list[dict[str, Any]]]:
    """Return all canonical A2UI v0.9 surfaces for CLI and unit-test verification."""
    return {
        "incident_triage_card": build_incident_triage_surface(),
        "hitl_confirmation_gate": build_hitl_confirmation_surface(),
        "hitl_receipt_update": build_hitl_receipt_update_surface(),
        "fleet_finops_explorer": build_fleet_finops_explorer_surface(),
        "sre_command_center_iframe": build_sre_command_center_iframe_surface(),
    }

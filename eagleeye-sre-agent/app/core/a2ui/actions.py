# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Deterministic inbound a2ui_action parser and surface dispatcher."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.core.a2ui.surfaces import (
    build_fleet_finops_explorer_surface,
    build_hitl_confirmation_surface,
    build_hitl_receipt_update_surface,
    build_incident_triage_surface,
    build_sre_command_center_iframe_surface,
)


@dataclass(frozen=True)
class InboundA2UIAction:
    """Normalized representation of an inbound A2UI user action or postMessage payload."""

    action: str
    prompt: str
    data: dict[str, Any]
    surface_id: str | None = None


def _parse_button_prompt_text(text: str) -> InboundA2UIAction | None:
    """Detect exact button prompt strings emitted by EagleEye A2UI surfaces when sent as plain text."""
    stripped = text.strip()
    lower = stripped.lower()
    if lower.startswith("scale regional hyperdisk balanced ha in "):
        return InboundA2UIAction(
            action="scale_hyperdisk_iops",
            prompt=stripped,
            data={"region": "europe-west2", "targetIops": 320000, "targetThroughputMib": 12000},
        )
    if lower.startswith("approve and execute act-hd-scale-320k"):
        return InboundA2UIAction(
            action="confirm_hitl_execution",
            prompt=stripped,
            data={
                "surfaceId": "sre-hitl-confirmation-gate",
                "actionId": "ACT-HD-SCALE-320K",
                "targetDisk": "loyalty-mysql-prod-eu-west2-hd-ha",
                "region": "europe-west2",
                "requestedIops": 320000,
                "requestedThroughputMib": 12000,
            },
            surface_id="sre-hitl-confirmation-gate",
        )
    if lower.startswith("cancel infrastructure modification act-hd-scale-320k"):
        return InboundA2UIAction(
            action="cancel_hitl_execution",
            prompt=stripped,
            data={
                "surfaceId": "sre-hitl-confirmation-gate",
                "actionId": "ACT-HD-SCALE-320K",
                "targetDisk": "loyalty-mysql-prod-eu-west2-hd-ha",
            },
            surface_id="sre-hitl-confirmation-gate",
        )
    if lower.startswith("drain pos traffic from exhausted zone "):
        return InboundA2UIAction(
            action="drain_exhausted_zone",
            prompt=stripped,
            data={"incidentId": "INC-2026-8841", "region": "europe-west2", "zone": "europe-west2-b"},
        )
    if lower.startswith("create an atlassian rovo jira p1 incident ticket for "):
        return InboundA2UIAction(
            action="create_jira_incident",
            prompt=stripped,
            data={"incidentId": "INC-2026-8841", "region": "europe-west2"},
        )
    if lower.startswith("generate a 1-click blameless postmortem in google docs and executive slides for "):
        return InboundA2UIAction(
            action="draft_workspace_postmortem",
            prompt=stripped,
            data={"incidentId": "INC-2026-8841", "region": "europe-west2"},
        )
    if lower == "open the interactive eagleeye sre command center workbench in the side-panel canvas.":
        return InboundA2UIAction(
            action="open_sre_command_center",
            prompt=stripped,
            data={"activeTab": "capacity"},
        )
    if lower.startswith("stage retirement of 72 idle warm-standby vms"):
        return InboundA2UIAction(
            action="stage_idle_reservation_retirement",
            prompt=stripped,
            data={"retiredVmCount": 72},
        )
    return None


def parse_inbound_a2ui_action(raw_input: str | dict[str, Any]) -> InboundA2UIAction | None:
    """Parse an inbound a2ui_action payload from JSON string, dict, or A2UI event envelope."""
    payload: dict[str, Any] | None = None
    if isinstance(raw_input, dict):
        payload = raw_input
    elif isinstance(raw_input, str):
        stripped = raw_input.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    payload = parsed
            except json.JSONDecodeError:
                payload = None
        else:
            return _parse_button_prompt_text(stripped)

    if not payload:
        return None

    # Format 1: React iframe bridge `{ "type": "a2ui_action", "action": "...", "data": { "prompt": "...", ... } }`
    if payload.get("type") == "a2ui_action" and isinstance(payload.get("action"), str):
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        prompt = str(data.get("prompt") or f"Execute {payload['action']}")
        surface_id = data.get("surfaceId") if isinstance(data.get("surfaceId"), str) else None
        return InboundA2UIAction(
            action=payload["action"],
            prompt=prompt,
            data=data,
            surface_id=surface_id,
        )

    # Format 2: Native A2UI v0.9 button event `{ "event": { "name": "...", "context": { "prompt": "..." } } }`
    # or Gemini Enterprise `{ "userAction": { "name": "...", "surfaceId": "...", "context": { ... } } }`
    # or `{ "action": { "name": "...", "surfaceId": "...", "context": { ... } } }`
    for key in ("event", "userAction", "action"):
        if isinstance(payload.get(key), dict):
            evt = payload[key]
            name = evt.get("name") or evt.get("actionName")
            ctx = evt.get("context") if isinstance(evt.get("context"), dict) else {}
            if isinstance(name, str) and name:
                prompt = str(ctx.get("prompt") or f"Execute {name}")
                surface_id = (
                    evt.get("surfaceId")
                    if isinstance(evt.get("surfaceId"), str)
                    else (ctx.get("surfaceId") if isinstance(ctx.get("surfaceId"), str) else None)
                )
                return InboundA2UIAction(
                    action=name,
                    prompt=prompt,
                    data=ctx,
                    surface_id=surface_id,
                )

    return None


def dispatch_a2ui_action(inbound: InboundA2UIAction) -> dict[str, Any]:
    """Deterministically execute an inbound A2UI action and return prose + updated A2UI v0.9 messages."""
    act = inbound.action
    data = inbound.data

    if act == "scale_hyperdisk_iops":
        region = str(data.get("region", "europe-west2"))
        target_iops = int(data.get("targetIops", 320000))
        target_tput = int(data.get("targetThroughputMib", 12000))
        disk_name = str(data.get("targetDisk", f"loyalty-mysql-prod-{region}-hd-ha"))
        surfaces = build_hitl_confirmation_surface(
            action_id="ACT-HD-SCALE-320K",
            target_disk=disk_name,
            target_region=region,
            requested_iops=target_iops,
            requested_throughput_mib=target_tput,
        )
        return {
            "status": "HITL_GATE_OPENED",
            "action": act,
            "summary": (
                f"Staged HITL confirmation gate to scale {disk_name} in {region} "
                f"to {target_iops:,} IOPS and {target_tput:,} MiB/s."
            ),
            "a2ui_messages": surfaces,
        }

    if act in ("confirm_hitl_execution", "cancel_hitl_execution"):
        surface_id = inbound.surface_id or str(data.get("surfaceId", "sre-hitl-confirmation-gate"))
        action_id = str(data.get("actionId", "ACT-HD-SCALE-320K"))
        target_disk = str(data.get("targetDisk", "loyalty-mysql-prod-eu-west2-hd-ha"))
        if act == "confirm_hitl_execution":
            req_iops = int(data.get("requestedIops", 320000))
            req_tput = int(data.get("requestedThroughputMib", 12000))
            status_label = "EXECUTED"
            summary_text = (
                f"Confirmed and executed {action_id} on {target_disk}: scaled Regional Hyperdisk "
                f"Balanced HA to {req_iops:,} IOPS / {req_tput:,} MiB/s (RPO=0, Torn-Write Protection "
                f"enabled, next dynamic scaling window available in 4 hours)."
            )
        else:
            status_label = "CANCELLED"
            summary_text = (
                f"Cancelled infrastructure modification {action_id} on {target_disk}. "
                f"No changes were applied."
            )
        surfaces = build_hitl_receipt_update_surface(
            action_id=action_id,
            target_disk=target_disk,
            status=status_label,
            summary=summary_text,
            surface_id=surface_id,
        )
        return {
            "status": status_label,
            "action": act,
            "summary": summary_text,
            "a2ui_messages": surfaces,
        }

    if act == "drain_exhausted_zone":
        incident_id = str(data.get("incidentId", "INC-2026-8841"))
        region = str(data.get("region", "europe-west2"))
        zone = str(data.get("zone", "europe-west2-b"))
        surfaces = build_incident_triage_surface(
            incident_id=incident_id,
            region=region,
            exhausted_zone=zone,
            p99_latency_ms=194.2,
            active_step_index=2,
        )
        return {
            "status": "MITIGATING",
            "action": act,
            "summary": (
                f"Drained POS traffic from {zone} and rebalanced to C4/N4 node pools across "
                f"healthy zones in {region}. POS p99 latency dropped to 194.2 ms (within <250ms SLA)."
            ),
            "a2ui_messages": surfaces,
        }

    if act == "create_jira_incident":
        incident_id = str(data.get("incidentId", "INC-2026-8841"))
        region = str(data.get("region", "europe-west2"))
        summary_text = (
            f"Created Atlassian Rovo Jira P1 Incident Ticket SRE-9412 for {incident_id} ({region}) "
            f"grounded on Confluence runbook CONF-RB-402 (Zonal Exhaustion & Hyperdisk Balanced HA Failover)."
        )
        surfaces = build_hitl_receipt_update_surface(
            action_id="JIRA-SRE-9412",
            target_disk=f"{incident_id} ({region})",
            status="CREATED",
            summary=summary_text,
            surface_id="sre-jira-ticket-receipt",
            include_create_surface=True,
        )
        return {
            "status": "CREATED",
            "action": act,
            "summary": summary_text,
            "a2ui_messages": surfaces,
        }

    if act == "draft_workspace_postmortem":
        incident_id = str(data.get("incidentId", "INC-2026-8841"))
        region = str(data.get("region", "europe-west2"))
        summary_text = (
            f"Generated 1-Click Google Workspace Blameless Postmortem Doc (DOC-PM-8841), Executive "
            f"Briefing Deck (SLIDES-PM-8841), and FinOps/SLO Timeline Sheet (SHEETS-PM-8841) for {incident_id} ({region})."
        )
        surfaces = build_hitl_receipt_update_surface(
            action_id="WORKSPACE-PM-8841",
            target_disk=f"{incident_id} ({region})",
            status="GENERATED",
            summary=summary_text,
            surface_id="sre-postmortem-receipt",
            include_create_surface=True,
        )
        return {
            "status": "GENERATED",
            "action": act,
            "summary": summary_text,
            "a2ui_messages": surfaces,
        }

    if act in ("open_sre_command_center", "switch_workbench_tab"):
        tab = str(data.get("activeTab", "capacity"))
        surfaces = build_sre_command_center_iframe_surface(active_tab=tab)
        return {
            "status": "WORKBENCH_OPENED",
            "action": act,
            "summary": f"Opened EagleEye SRE Command Center workbench on tab '{tab}'.",
            "a2ui_messages": surfaces,
        }

    if act in ("stage_idle_reservation_retirement", "open_fleet_finops_explorer"):
        surfaces = build_fleet_finops_explorer_surface()
        return {
            "status": "FINOPS_EXPLORER_UPDATED",
            "action": act,
            "summary": "Rendered Global Retail Fleet & FinOps Explorer with idle reservation retirement plan.",
            "a2ui_messages": surfaces,
        }

    # Generic deterministic receipt for any custom action emitted from the 4 workbench tabs
    action_id = str(data.get("actionId", f"ACT-{act.upper()[:16]}"))
    target_resource = str(data.get("targetResource", data.get("region", "global-retail-fleet")))
    summary_text = (
        f"Executed SRE workbench action '{act}' on {target_resource}: {inbound.prompt}"
    )
    surfaces = build_hitl_receipt_update_surface(
        action_id=action_id,
        target_disk=target_resource,
        status="COMPLETED",
        summary=summary_text,
        surface_id=inbound.surface_id or "sre-workbench-action-receipt",
        include_create_surface=inbound.surface_id is None,
    )
    return {
        "status": "COMPLETED",
        "action": act,
        "summary": summary_text,
        "a2ui_messages": surfaces,
    }

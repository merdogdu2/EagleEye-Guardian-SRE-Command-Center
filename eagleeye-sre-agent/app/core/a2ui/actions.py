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
    if isinstance(payload.get("event"), dict):
        evt = payload["event"]
        name = evt.get("name")
        ctx = evt.get("context") if isinstance(evt.get("context"), dict) else {}
        if isinstance(name, str) and name:
            prompt = str(ctx.get("prompt") or f"Execute {name}")
            surface_id = ctx.get("surfaceId") if isinstance(ctx.get("surfaceId"), str) else None
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
    )
    return {
        "status": "COMPLETED",
        "action": act,
        "summary": summary_text,
        "a2ui_messages": surfaces,
    }

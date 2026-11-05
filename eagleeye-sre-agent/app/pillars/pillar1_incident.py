# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Pillar 1 — Incident Triage, POS Latency & Postmortem Agent (incident_triage_agent)."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from app.core.config import GLOBAL_RETAIL_REGIONS, POS_P99_SLA_MS, settings
from app.core.guardrails import enforce_tool_output_budget


def correlate_pos_incident_telemetry(
    region: str = "europe-west2",
    incident_id: str = "INC-2026-8841",
) -> dict[str, Any]:
    """Correlate POS coupon/wallet p99 SLA (<250ms) metrics, GKE zonal events, and Error Reporting."""
    selected_region = region if region in GLOBAL_RETAIL_REGIONS else "europe-west2"
    regional_snapshots: dict[str, dict[str, Any]] = {
        "europe-west2": {
            "p99_latency_ms": 682.4,
            "p95_latency_ms": 412.0,
            "sla_breached": True,
            "exhausted_zone": "europe-west2-b",
            "gce_event": "ZONE_RESOURCE_POOL_EXHAUSTED",
            "legacy_family_impacted": "n1-standard-32",
            "storage_bottleneck": "Zonal SSD PD capped at 100,000 IOPS / 1,200 MiB/s",
            "error_rate_pct": 3.85,
            "top_error_signature": "DEADLINE_EXCEEDED: CouponRedemptionLedger.CommitTransaction",
        },
        "europe-west1": {
            "p99_latency_ms": 174.2,
            "p95_latency_ms": 118.5,
            "sla_breached": False,
            "exhausted_zone": None,
            "gce_event": "NOMINAL",
            "legacy_family_impacted": None,
            "storage_bottleneck": "None (Regional Hyperdisk Balanced HA active)",
            "error_rate_pct": 0.04,
            "top_error_signature": "NONE",
        },
        "us-east1": {
            "p99_latency_ms": 241.8,
            "p95_latency_ms": 169.0,
            "sla_breached": False,
            "exhausted_zone": "us-east1-c",
            "gce_event": "ZONE_RESOURCE_POOL_EXHAUSTED_WARNING",
            "legacy_family_impacted": "n1-highmem-16",
            "storage_bottleneck": "Approaching 92,000 / 100,000 IOPS on Zonal SSD PD",
            "error_rate_pct": 0.31,
            "top_error_signature": "RESOURCE_EXHAUSTED: ConnectionPoolWaitTimeout",
        },
        "us-east4": {
            "p99_latency_ms": 152.0,
            "p95_latency_ms": 104.2,
            "sla_breached": False,
            "exhausted_zone": None,
            "gce_event": "NOMINAL",
            "legacy_family_impacted": None,
            "storage_bottleneck": "None",
            "error_rate_pct": 0.02,
            "top_error_signature": "NONE",
        },
        "australia-southeast1": {
            "p99_latency_ms": 218.5,
            "p95_latency_ms": 149.1,
            "sla_breached": False,
            "exhausted_zone": None,
            "gce_event": "NOMINAL",
            "legacy_family_impacted": "n1-standard-16",
            "storage_bottleneck": "Zonal SSD PD at 78% IOPS utilization",
            "error_rate_pct": 0.11,
            "top_error_signature": "NONE",
        },
        "australia-southeast2": {
            "p99_latency_ms": 161.3,
            "p95_latency_ms": 112.0,
            "sla_breached": False,
            "exhausted_zone": None,
            "gce_event": "NOMINAL",
            "legacy_family_impacted": None,
            "storage_bottleneck": "None",
            "error_rate_pct": 0.03,
            "top_error_signature": "NONE",
        },
    }

    target = regional_snapshots[selected_region]
    payload: dict[str, Any] = {
        "status": "SLA_BREACH_CORRELATED" if target["sla_breached"] else "HEALTHY_WITHIN_SLA",
        "incident_id": incident_id,
        "region": selected_region,
        "pos_p99_sla_ms": POS_P99_SLA_MS,
        "monitored_regions": list(GLOBAL_RETAIL_REGIONS),
        "telemetry": target,
        "global_summary": {
            r: {
                "p99_latency_ms": snap["p99_latency_ms"],
                "sla_breached": snap["sla_breached"],
                "gce_event": snap["gce_event"],
            }
            for r, snap in regional_snapshots.items()
        },
        "recommended_remediation": [
            f"Drain legacy N1 pod pools in {target['exhausted_zone'] or selected_region} and shift traffic to C4/N4 multi-zone node pools.",
            "Dynamically scale Regional Hyperdisk Balanced HA to 320,000 IOPS / 12,000 MiB/s with Torn-Write Protection.",
            "Trigger Atlassian Rovo runbook grounding and create a P1 Jira incident.",
        ],
        "war_room_context": {
            "hitl_gate_action": "ACT-HD-SCALE-320K (Scale loyalty-mysql-prod-eu-west2-hd-ha to 320,000 IOPS / 12,000 MiB/s, RPO=0, <2.5m RTO, Torn-Write Protection enabled, 1x/4h scaling window)",
            "fleet_finops_summary": "159 legacy N1 VMs exiting to C4/N4/C3 across 6 regions; retiring 72 idle warm-standby VMs saves $214,100/month ($2.57M/year)",
            "gpu_advisor_summary": "NVIDIA RTX PRO 6000 (g4-standard-384): DWS Flex-start recommended for uninterrupted 7-day runs; Spot VMs for fault-tolerant checkpointed workloads",
        },
        "ui_hint": "[surface:incident]",
    }
    return enforce_tool_output_budget(payload)


def ground_and_create_rovo_incident(
    incident_id: str = "INC-2026-8841",
    region: str = "europe-west2",
    summary: str = "POS coupon redemption p99 latency spike (682.4ms vs <250ms SLA) caused by ZONE_RESOURCE_POOL_EXHAUSTED + Zonal SSD PD IOPS saturation",
    priority: str = "P1",
) -> dict[str, Any]:
    """Ground SRE runbooks via Atlassian Rovo (Confluence) and create a linked Jira incident ticket."""
    payload: dict[str, Any] = {
        "status": "ROVO_JIRA_CREATED",
        "connector": "Atlassian Rovo Federated Connector",
        "incident_id": incident_id,
        "region": region,
        "jira_ticket": {
            "key": "SRE-4921",
            "priority": priority,
            "title": f"[{priority}] {incident_id} ({region}): {summary[:100]}",
            "url": "https://jira.example.com/browse/SRE-4921",
            "assignee": "EagleEye On-Call Primary",
            "labels": ["pos-sla", "zone-exhaustion", "hyperdisk-ha", region],
        },
        "confluence_runbooks_grounded": [
            {
                "page_id": "CONF-RB-104",
                "title": "Runbook: Mitigating ZONE_RESOURCE_POOL_EXHAUSTED via C4/N4 Cross-Family Spillover",
                "relevance_score": 0.97,
            },
            {
                "page_id": "CONF-RB-219",
                "title": "Runbook: MySQL Zonal SSD PD to Regional Hyperdisk Balanced HA Failover & IOPS Scaling",
                "relevance_score": 0.95,
            },
        ],
    }
    return enforce_tool_output_budget(payload)


def generate_workspace_blameless_postmortem(
    incident_id: str = "INC-2026-8841",
    region: str = "europe-west2",
    jira_key: str = "SRE-4921",
    peak_p99_ms: float = 682.4,
    recovered_p99_ms: float = 188.0,
) -> dict[str, Any]:
    """Generate 1-click blameless postmortem Doc, executive Slides deck, and SLA timeline Sheet via Google Workspace connector."""
    payload: dict[str, Any] = {
        "status": "WORKSPACE_ARTIFACTS_GENERATED",
        "connector": "Google Workspace Federated Connector",
        "incident_id": incident_id,
        "jira_key": jira_key,
        "region": region,
        "artifacts": {
            "google_doc_postmortem": {
                "doc_id": f"doc-pm-{incident_id.lower()}",
                "title": f"[Blameless Postmortem] {incident_id}: {region} POS Coupon Redemption SLA Breach",
                "url": f"https://docs.google.com/document/d/example-{incident_id.lower()}",
                "sections": [
                    "Executive Summary & Customer Impact (Peak p99: 682.4ms vs <250ms SLA)",
                    "Root Cause: N1 Zonal Stockout (ZONE_RESOURCE_POOL_EXHAUSTED) + Zonal SSD PD 100k IOPS Ceiling",
                    "What Went Well: Automated detection & <2.5m RTO failover on Regional Hyperdisk Balanced HA",
                    "Action Items: Complete N1->C4/N4 exit & enable Torn-Write Protection across all 6 regions",
                ],
            },
            "google_slides_exec_briefing": {
                "presentation_id": f"slides-exec-{incident_id.lower()}",
                "title": f"Executive Reliability Briefing — {incident_id} ({region})",
                "url": f"https://docs.google.com/presentation/d/example-{incident_id.lower()}",
                "slide_count": 6,
            },
            "google_sheets_sla_timeline": {
                "spreadsheet_id": f"sheet-sla-{incident_id.lower()}",
                "title": f"{incident_id} Minute-by-Minute POS p99 Telemetry & Error Budget Burn",
                "url": f"https://docs.google.com/spreadsheets/d/example-{incident_id.lower()}",
                "peak_p99_ms": peak_p99_ms,
                "recovered_p99_ms": recovered_p99_ms,
            },
        },
    }
    return enforce_tool_output_budget(payload)


incident_triage_agent = LlmAgent(
    name="incident_triage_agent",
    model=settings.specialist_model,
    description=(
        "Pillar 1 Specialist: Real-time retail POS coupon & loyalty wallet SLA (<250ms p99) "
        "incident triage across global regions, correlating Cloud Monitoring latency spikes, "
        "ZONE_RESOURCE_POOL_EXHAUSTED events, Atlassian Rovo runbooks/Jira, and Google Workspace postmortems."
    ),
    instruction=(
        "You are the Pillar 1 Incident Triage, POS Latency & Postmortem Specialist for EagleEye Guardian. "
        "Monitor the <250ms p99 SLA across europe-west2, europe-west1, us-east1, us-east4, "
        "australia-southeast1, and australia-southeast2. Correlate p99 spikes with "
        "ZONE_RESOURCE_POOL_EXHAUSTED and Zonal SSD PD 100k IOPS bottlenecks, ground Confluence "
        "runbooks and create Jira tickets via Atlassian Rovo, and generate 1-click blameless "
        "postmortems in Google Docs, Slides, and Sheets. Include '[surface:incident]' when "
        "presenting live incident triage cards."
    ),
    tools=[
        correlate_pos_incident_telemetry,
        ground_and_create_rovo_incident,
        generate_workspace_blameless_postmortem,
    ],
)

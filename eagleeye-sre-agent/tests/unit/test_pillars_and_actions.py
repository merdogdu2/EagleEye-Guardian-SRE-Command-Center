# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for all 4 SRE Pillars, tool budget compliance, and inbound a2ui_action dispatch."""

from __future__ import annotations

import json

from google.adk.models.llm_request import LlmRequest
from google.genai.types import Content, Part

from app.core.a2ui.actions import dispatch_a2ui_action, parse_inbound_a2ui_action
from app.core.a2ui.primitives import extract_a2ui_messages_from_part, validate_a2ui_envelope
from app.core.config import MAX_TOOL_OUTPUT_BYTES
from app.core.guardrails import before_model_call
from app.pillars.pillar1_incident import (
    correlate_pos_incident_telemetry,
    generate_workspace_blameless_postmortem,
    ground_and_create_rovo_incident,
)
from app.pillars.pillar2_capacity import (
    advise_g4_gpu_placement,
    audit_bfcm_n1_exit_and_headroom,
    audit_idle_reservations_vs_cuds,
)
from app.pillars.pillar3_database import (
    model_hyperdisk_balanced_ha_migration,
    optimize_snapshot_recycle_bin,
    run_cloud_spanner_ledger_load_test,
    spanner_load_test_long_running_tool,
)
from app.pillars.pillar4_security import (
    check_gemini_enterprise_connectors,
    diagnose_vpc_sc_audit_violations,
)


def _assert_within_budget(result: dict[str, object]) -> None:
    encoded = json.dumps(result).encode("utf-8")
    assert len(encoded) <= MAX_TOOL_OUTPUT_BYTES


def test_pillar1_incident_tools() -> None:
    """Verify Pillar 1 POS latency correlation, Atlassian Rovo, and Google Workspace tools."""
    corr = correlate_pos_incident_telemetry(region="europe-west2", incident_id="INC-2026-8841")
    _assert_within_budget(corr)
    assert corr["status"] == "SLA_BREACH_CORRELATED"
    assert corr["telemetry"]["gce_event"] == "ZONE_RESOURCE_POOL_EXHAUSTED"

    rovo = ground_and_create_rovo_incident(incident_id="INC-2026-8841", region="europe-west2")
    _assert_within_budget(rovo)
    assert rovo["status"] == "ROVO_JIRA_CREATED"
    assert len(rovo["confluence_runbooks_grounded"]) >= 2

    pm = generate_workspace_blameless_postmortem(incident_id="INC-2026-8841", region="europe-west2")
    _assert_within_budget(pm)
    assert "google_doc_postmortem" in pm["artifacts"]
    assert "google_slides_exec_briefing" in pm["artifacts"]
    assert "google_sheets_sla_timeline" in pm["artifacts"]


def test_pillar2_capacity_and_g4_gpu_advisor() -> None:
    """Verify Pillar 2 N1 exit matrix, Idle Reservation vs. CUD audit, and G4 GPU Placement Advisor."""
    bfcm = audit_bfcm_n1_exit_and_headroom()
    _assert_within_budget(bfcm)
    assert bfcm["status"] == "BFCM_CAPACITY_AUDITED"
    assert bfcm["total_legacy_n1_remaining"] > 0

    res_audit = audit_idle_reservations_vs_cuds()
    _assert_within_budget(res_audit)
    assert res_audit["total_idle_standby_vms_to_retire"] == 72
    assert res_audit["annual_idle_reservation_savings_usd"] > 0

    spot = advise_g4_gpu_placement(workload_type="checkpointed_training", duration_days=3.0)
    _assert_within_budget(spot)
    assert spot["machine_type"] == "g4-standard-384"
    assert spot["recommended_consumption_model"] == "SPOT_VM"

    dws = advise_g4_gpu_placement(workload_type="uninterrupted_dense_sync", duration_days=5.0)
    _assert_within_budget(dws)
    assert dws["recommended_consumption_model"] == "DWS_FLEX_START"

    spill = advise_g4_gpu_placement(workload_type="uninterrupted_long_run", duration_days=14.0)
    _assert_within_budget(spill)
    assert spill["recommended_consumption_model"] == "CROSS_REGION_SPILLOVER"


def test_pillar3_database_hyperdisk_and_spanner_long_running_tool() -> None:
    """Verify Pillar 3 Regional Hyperdisk Balanced HA modeling and Cloud Spanner LongRunningFunctionTool."""
    hd = model_hyperdisk_balanced_ha_migration(
        capacity_tib=64,
        target_iops=640000,
        target_throughput_mib=20000,
        enable_torn_write_protection=True,
    )
    _assert_within_budget(hd)
    assert hd["target_posture"]["provisioned_iops"] == 640000
    assert hd["target_posture"]["provisioned_throughput_mib_s"] == 20000
    assert "RPO=0" in hd["target_posture"]["rpo"]

    recycle = optimize_snapshot_recycle_bin()
    _assert_within_budget(recycle)
    assert recycle["reclaimed_snapshot_capacity_tib"] > 0

    spanner = run_cloud_spanner_ledger_load_test(target_qps=150000, use_interleaved_tables=True)
    _assert_within_budget(spanner)
    assert spanner["status"] == "SPANNER_LOAD_TEST_COMPLETED"
    assert spanner["latency_metrics"]["p99_write_ms"] < 250.0
    assert spanner_load_test_long_running_tool.func is run_cloud_spanner_ledger_load_test


def test_pillar4_security_vpc_sc_and_connectors() -> None:
    """Verify Pillar 4 VPC-SC violation diagnostics and Gemini Enterprise connector health checks."""
    vpc = diagnose_vpc_sc_audit_violations()
    _assert_within_budget(vpc)
    reasons = {v["violation_reason"] for v in vpc["violations_analyzed"]}
    assert {
        "SECURITY_POLICY_VIOLATED",
        "SERVICE_NOT_ALLOWED_FROM_VPC",
        "NO_MATCHING_ACCESS_LEVEL",
    }.issubset(reasons)
    assert "gcloud access-context-manager perimeters update" in vpc["remediation_gcloud_cli"]
    assert "google_access_context_manager_service_perimeter" in vpc["remediation_terraform_hcl"]

    conn = check_gemini_enterprise_connectors()
    _assert_within_budget(conn)
    assert conn["status"] == "CONNECTORS_HEALTHY"
    assert conn["total_connectors"] == 3


def test_inbound_a2ui_action_bridge_and_in_place_hitl_receipt() -> None:
    """Verify deterministic interception of iframe postMessage and in-place HITL surface update."""
    iframe_msg = json.dumps(
        {
            "type": "a2ui_action",
            "action": "confirm_hitl_execution",
            "data": {
                "prompt": "Approve scaling Regional Hyperdisk Balanced HA to 320,000 IOPS",
                "surfaceId": "sre-hitl-confirmation-gate",
                "actionId": "ACT-HD-SCALE-320K",
                "targetDisk": "loyalty-mysql-prod-eu-west2-hd-ha",
                "requestedIops": 320000,
                "requestedThroughputMib": 12000,
            },
        }
    )
    parsed = parse_inbound_a2ui_action(iframe_msg)
    assert parsed is not None
    assert parsed.action == "confirm_hitl_execution"
    assert parsed.surface_id == "sre-hitl-confirmation-gate"

    dispatched = dispatch_a2ui_action(parsed)
    assert dispatched["status"] == "EXECUTED"
    messages = dispatched["a2ui_messages"]
    assert not validate_a2ui_envelope(messages)
    # In-place update uses updateComponents on the same surfaceId without createSurface
    assert len(messages) == 1
    assert "updateComponents" in messages[0]
    assert messages[0]["updateComponents"]["surfaceId"] == "sre-hitl-confirmation-gate"

    # Also verify before_model_call deterministically intercepts the user message
    req = LlmRequest(contents=[Content(role="user", parts=[Part.from_text(text=iframe_msg)])])
    llm_resp = before_model_call(None, req)
    assert llm_resp is not None and llm_resp.content is not None
    parts = llm_resp.content.parts or []
    assert len(parts) == 2
    extracted = extract_a2ui_messages_from_part(parts[1])
    assert extracted == messages

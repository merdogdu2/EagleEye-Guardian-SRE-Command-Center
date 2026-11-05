# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Pillar 2 — Multi-Region Capacity Shield & GPU Placement Agent (capacity_shield_agent)."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from app.core.config import GLOBAL_RETAIL_REGIONS, settings
from app.core.guardrails import enforce_tool_output_budget


def audit_bfcm_n1_exit_and_headroom(
    region_filter: str = "all",
) -> dict[str, Any]:
    """Audit legacy 1st-Gen N1 VM exit to Gen 3/4 (C4, N4, C3, C3D) and BFCM multi-zone spillover readiness."""
    matrix: list[dict[str, Any]] = [
        {
            "region": "europe-west2",
            "legacy_n1_vms": 42,
            "target_families": ["c4-standard-32", "n4-standard-32", "c3-standard-44"],
            "modern_gen3_gen4_vms": 180,
            "bfcm_peak_headroom_pct": 34.5,
            "zonal_exhaustion_risk": "HIGH_ON_N1_ONLY",
            "cross_family_spillover_order": ["c4-standard-32", "n4-standard-32", "c3-standard-44", "c3d-standard-30"],
        },
        {
            "region": "europe-west1",
            "legacy_n1_vms": 18,
            "target_families": ["c4-standard-32", "n4-standard-32", "c3d-standard-30"],
            "modern_gen3_gen4_vms": 140,
            "bfcm_peak_headroom_pct": 46.0,
            "zonal_exhaustion_risk": "LOW",
            "cross_family_spillover_order": ["n4-standard-32", "c4-standard-32", "c3d-standard-30"],
        },
        {
            "region": "us-east1",
            "legacy_n1_vms": 55,
            "target_families": ["c4-standard-48", "n4-highmem-32", "c3-standard-44"],
            "modern_gen3_gen4_vms": 220,
            "bfcm_peak_headroom_pct": 31.0,
            "zonal_exhaustion_risk": "MODERATE_ON_N1",
            "cross_family_spillover_order": ["c4-standard-48", "n4-highmem-32", "c3-standard-44", "c3d-standard-60"],
        },
        {
            "region": "us-east4",
            "legacy_n1_vms": 12,
            "target_families": ["c4-standard-32", "n4-standard-32"],
            "modern_gen3_gen4_vms": 160,
            "bfcm_peak_headroom_pct": 52.0,
            "zonal_exhaustion_risk": "LOW",
            "cross_family_spillover_order": ["c4-standard-32", "n4-standard-32", "c3-standard-22"],
        },
        {
            "region": "australia-southeast1",
            "legacy_n1_vms": 24,
            "target_families": ["c4-standard-32", "n4-standard-32", "c3-standard-22"],
            "modern_gen3_gen4_vms": 96,
            "bfcm_peak_headroom_pct": 38.0,
            "zonal_exhaustion_risk": "MODERATE_ON_N1",
            "cross_family_spillover_order": ["n4-standard-32", "c4-standard-32", "c3-standard-22"],
        },
        {
            "region": "australia-southeast2",
            "legacy_n1_vms": 8,
            "target_families": ["n4-standard-32", "c3-standard-22"],
            "modern_gen3_gen4_vms": 74,
            "bfcm_peak_headroom_pct": 54.0,
            "zonal_exhaustion_risk": "LOW",
            "cross_family_spillover_order": ["n4-standard-32", "c3-standard-22"],
        },
    ]
    if region_filter != "all" and region_filter in GLOBAL_RETAIL_REGIONS:
        matrix = [row for row in matrix if row["region"] == region_filter]

    total_n1 = sum(r["legacy_n1_vms"] for r in matrix)
    total_modern = sum(r["modern_gen3_gen4_vms"] for r in matrix)
    payload: dict[str, Any] = {
        "status": "BFCM_CAPACITY_AUDITED",
        "total_legacy_n1_remaining": total_n1,
        "total_modern_gen3_gen4_vms": total_modern,
        "modernization_completion_pct": round(
            (total_modern / max(1, total_n1 + total_modern)) * 100.0, 2
        ),
        "regional_matrix": matrix,
        "bfcm_policy": (
            "Enforce multi-zone pod topology spread and automatic cross-family spillover "
            "(C4 -> N4 -> C3 -> C3D) to eliminate single-zone N1 stockout risk during BFCM."
        ),
        "ui_hint": "[surface:explorer]",
    }
    return enforce_tool_output_budget(payload)


def audit_idle_reservations_vs_cuds(
    retired_standby_vm_unit_cost_usd: float = 1150.0,
) -> dict[str, Any]:
    """Audit Idle Standby Compute Reservations vs. CUDs where Regional Hyperdisk Balanced HA eliminates warm standby VMs."""
    regional_audit: list[dict[str, Any]] = [
        {
            "region": "europe-west2",
            "idle_standby_vms": 16,
            "cud_coverage_pct": 84.0,
            "eliminated_by": "Regional Hyperdisk Balanced HA synchronous RPO=0 replication",
            "monthly_waste_reclaimed_usd": round(16 * retired_standby_vm_unit_cost_usd, 2),
        },
        {
            "region": "europe-west1",
            "idle_standby_vms": 12,
            "cud_coverage_pct": 88.0,
            "eliminated_by": "Regional Hyperdisk Balanced HA synchronous RPO=0 replication",
            "monthly_waste_reclaimed_usd": round(12 * retired_standby_vm_unit_cost_usd, 2),
        },
        {
            "region": "us-east1",
            "idle_standby_vms": 20,
            "cud_coverage_pct": 81.5,
            "eliminated_by": "Regional Hyperdisk Balanced HA synchronous RPO=0 replication",
            "monthly_waste_reclaimed_usd": round(20 * retired_standby_vm_unit_cost_usd, 2),
        },
        {
            "region": "us-east4",
            "idle_standby_vms": 8,
            "cud_coverage_pct": 91.0,
            "eliminated_by": "Regional Hyperdisk Balanced HA synchronous RPO=0 replication",
            "monthly_waste_reclaimed_usd": round(8 * retired_standby_vm_unit_cost_usd, 2),
        },
        {
            "region": "australia-southeast1",
            "idle_standby_vms": 10,
            "cud_coverage_pct": 79.0,
            "eliminated_by": "Regional Hyperdisk Balanced HA synchronous RPO=0 replication",
            "monthly_waste_reclaimed_usd": round(10 * retired_standby_vm_unit_cost_usd, 2),
        },
        {
            "region": "australia-southeast2",
            "idle_standby_vms": 6,
            "cud_coverage_pct": 86.0,
            "eliminated_by": "Regional Hyperdisk Balanced HA synchronous RPO=0 replication",
            "monthly_waste_reclaimed_usd": round(6 * retired_standby_vm_unit_cost_usd, 2),
        },
    ]
    total_idle_vms = sum(r["idle_standby_vms"] for r in regional_audit)
    monthly_reclaimed = sum(r["monthly_waste_reclaimed_usd"] for r in regional_audit)
    payload: dict[str, Any] = {
        "status": "RESERVATION_AUDIT_COMPLETE",
        "total_idle_standby_vms_to_retire": total_idle_vms,
        "monthly_idle_reservation_savings_usd": round(monthly_reclaimed, 2),
        "annual_idle_reservation_savings_usd": round(monthly_reclaimed * 12.0, 2),
        "regional_breakdown": regional_audit,
        "recommendation": (
            "Retire warm standby database VMs held in idle zonal reservations; convert baseline "
            "stateless compute to 3-year Flexible CUDs across C4/N4/C3 families."
        ),
    }
    return enforce_tool_output_budget(payload)


def advise_g4_gpu_placement(
    workload_type: str = "checkpointed_training",
    requested_gpus: int = 64,
    duration_days: float = 5.0,
    preferred_region: str = "europe-west2",
) -> dict[str, Any]:
    """Evaluate G4 (NVIDIA RTX PRO 6000) zonal availability across Spot (g4-standard-384), DWS Flex-start (<=7d), and cross-region spillover."""
    is_fault_tolerant = "checkpoint" in workload_type.lower() or "batch" in workload_type.lower()
    fits_dws_window = duration_days <= 7.0

    if is_fault_tolerant:
        recommended_model = "SPOT_VM"
        rationale = (
            "Workload supports periodic checkpointing: deploy on Spot VMs (`g4-standard-384` "
            "with 8x NVIDIA RTX PRO 6000 GPUs per node) for up to 68% cost reduction with "
            "automated preemption resume."
        )
    elif fits_dws_window:
        recommended_model = "DWS_FLEX_START"
        rationale = (
            f"Uninterrupted run ({duration_days} days <= 7-day cap): use Dynamic Workload "
            "Scheduler (DWS) Flex-start on `g4-standard-384` to queue and co-allocate contiguous "
            "NVIDIA RTX PRO 6000 capacity without preemption."
        )
    else:
        recommended_model = "CROSS_REGION_SPILLOVER"
        rationale = (
            "Duration exceeds 7-day DWS Flex-start window and on-demand capacity in primary zone "
            "is subscribed; spillover to secondary region (`us-east4` or `europe-west1`)."
        )

    payload: dict[str, Any] = {
        "status": "GPU_PLACEMENT_EVALUATED",
        "accelerator": "NVIDIA RTX PRO 6000 (G4 Series)",
        "machine_type": "g4-standard-384",
        "requested_gpus": requested_gpus,
        "nodes_required": max(1, (requested_gpus + 7) // 8),
        "preferred_region": preferred_region,
        "duration_days": duration_days,
        "recommended_consumption_model": recommended_model,
        "rationale": rationale,
        "options_comparison": [
            {
                "model": "SPOT_VM",
                "machine_type": "g4-standard-384",
                "candidate_zones": ["europe-west2-a", "us-east1-b", "us-east4-c"],
                "estimated_discount_pct": 68.0,
                "max_run_duration_days": None,
                "best_for": "Fault-tolerant checkpointed training & batch visual-search inference",
            },
            {
                "model": "DWS_FLEX_START",
                "machine_type": "g4-standard-384",
                "candidate_zones": ["europe-west2-c", "europe-west1-b", "us-east4-a"],
                "estimated_discount_pct": 42.0,
                "max_run_duration_days": 7,
                "best_for": "Uninterrupted multi-node GPU runs up to 7 days without preemption",
            },
            {
                "model": "CROSS_REGION_SPILLOVER",
                "machine_type": "g4-standard-384",
                "candidate_zones": ["europe-west1-d", "us-east4-b", "australia-southeast1-a"],
                "estimated_discount_pct": 25.0,
                "max_run_duration_days": 30,
                "best_for": "Overflow capacity when primary region on-demand G4 pools are subscribed",
            },
        ],
    }
    return enforce_tool_output_budget(payload)


capacity_shield_agent = LlmAgent(
    name="capacity_shield_agent",
    model=settings.specialist_model,
    description=(
        "Pillar 2 Specialist: BFCM multi-region capacity shield, tracking legacy 1st-Gen N1 VM exit "
        "to Gen 3/4 (C4, N4, C3, C3D), Idle Standby Compute Reservation vs. CUD FinOps audits, "
        "and G4 (NVIDIA RTX PRO 6000) GPU placement across Spot, DWS Flex-start, and spillover."
    ),
    instruction=(
        "You are the Pillar 2 Multi-Region Capacity Shield & GPU Placement Specialist. "
        "Guide legacy N1 migration to C4/N4/C3/C3D with cross-family spillover for BFCM peaks, "
        "identify idle standby reservations made redundant by Regional Hyperdisk Balanced HA, "
        "and advise on G4 (NVIDIA RTX PRO 6000, `g4-standard-384`) GPU placement comparing "
        "Spot VMs, Dynamic Workload Scheduler (DWS) Flex-start (up to 7 days), and cross-region spillover."
    ),
    tools=[
        audit_bfcm_n1_exit_and_headroom,
        audit_idle_reservations_vs_cuds,
        advise_g4_gpu_placement,
    ],
)

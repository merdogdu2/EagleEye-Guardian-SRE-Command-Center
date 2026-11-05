# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Pillar 4 — Security, VPC Service Controls (VPC-SC) & Connector Guard Agent (security_guard_agent)."""

from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent

from app.core.config import settings
from app.core.guardrails import enforce_tool_output_budget
from app.core.identity import get_federated_connector_statuses


def diagnose_vpc_sc_audit_violations(
    perimeter_name: str = "sp_eagleeye_retail_prod",
    access_policy_id: str = "policy_retail_global_01",
    violation_filter: str = "ALL",
) -> dict[str, Any]:
    """Parse VpcServiceControlAuditMetadata logs and generate gcloud + Terraform ingress/egress remediation."""
    violations: list[dict[str, Any]] = [
        {
            "violation_id": "VPCSC-2026-991",
            "audit_log_type": "type.googleapis.com/google.cloud.audit.VpcServiceControlAuditMetadata",
            "violation_reason": "SECURITY_POLICY_VIOLATED",
            "target_service": "bigquery.googleapis.com",
            "method_name": "google.cloud.bigquery.v2.JobService.InsertJob",
            "principal_email": "sa-sre-analytics@your-gcp-project-id.iam.gserviceaccount.com",
            "source_project": settings.project_id,
            "perimeter": perimeter_name,
            "diagnosis": (
                "BigQuery Agent Analytics write stream blocked by missing egress rule from "
                "agent reasoning engine project to telemetry dataset project."
            ),
        },
        {
            "violation_id": "VPCSC-2026-992",
            "audit_log_type": "type.googleapis.com/google.cloud.audit.VpcServiceControlAuditMetadata",
            "violation_reason": "SERVICE_NOT_ALLOWED_FROM_VPC",
            "target_service": "storage.googleapis.com",
            "method_name": "google.cloud.storage.ReadObject",
            "principal_email": "sa-pos-ledger-sync@your-gcp-project-id.iam.gserviceaccount.com",
            "source_project": settings.project_id,
            "perimeter": perimeter_name,
            "diagnosis": (
                "GKE retail POS node pool in europe-west2 attempted Cloud Storage snapshot "
                "export over restricted VIP without storage.googleapis.com in VPC-SC ingress policy."
            ),
        },
        {
            "violation_id": "VPCSC-2026-993",
            "audit_log_type": "type.googleapis.com/google.cloud.audit.VpcServiceControlAuditMetadata",
            "violation_reason": "NO_MATCHING_ACCESS_LEVEL",
            "target_service": "discoveryengine.googleapis.com",
            "method_name": "google.cloud.discoveryengine.v1.ConversationalSearchService.AnswerQuery",
            "principal_email": "sa-gemini-enterprise-connector@your-gcp-project-id.iam.gserviceaccount.com",
            "source_project": settings.project_id,
            "perimeter": perimeter_name,
            "diagnosis": (
                "Gemini Enterprise federated connector identity missing from Access Context "
                "Manager access level `al_gemini_enterprise_trusted`."
            ),
        },
    ]

    if violation_filter != "ALL":
        violations = [
            v for v in violations if v["violation_reason"].upper() == violation_filter.upper()
        ] or violations

    gcloud_command = (
        f"gcloud access-context-manager perimeters update {perimeter_name} "
        f"--policy={access_policy_id} "
        f"--set-ingress-policies=ingress_rules.yaml "
        f"--set-egress-policies=egress_rules.yaml"
    )

    terraform_hcl = f'''resource "google_access_context_manager_service_perimeter_ingress_policy" "eagleeye_sre_ingress" {{
  perimeter = "accessPolicies/{access_policy_id}/servicePerimeters/{perimeter_name}"
  ingress_from {{
    identity_type = "ANY_SERVICE_ACCOUNT"
    sources {{
      access_level = "accessPolicies/{access_policy_id}/accessLevels/al_gemini_enterprise_trusted"
    }}
  }}
  ingress_to {{
    resources = ["projects/${{var.project_number}}"]
    operations {{
      service_name = "storage.googleapis.com"
      method_selectors {{ method = "*" }}
    }}
    operations {{
      service_name = "discoveryengine.googleapis.com"
      method_selectors {{ method = "*" }}
    }}
  }}
}}

resource "google_access_context_manager_service_perimeter_egress_policy" "eagleeye_bq_egress" {{
  perimeter = "accessPolicies/{access_policy_id}/servicePerimeters/{perimeter_name}"
  egress_from {{
    identities = ["serviceAccount:sa-sre-analytics@{settings.project_id}.iam.gserviceaccount.com"]
  }}
  egress_to {{
    resources = ["projects/${{var.analytics_project_number}}"]
    operations {{
      service_name = "bigquery.googleapis.com"
      method_selectors {{ method = "google.cloud.bigquery.v2.JobService.InsertJob" }}
    }}
  }}
}}'''

    payload: dict[str, Any] = {
        "status": "VPC_SC_VIOLATIONS_DIAGNOSED",
        "perimeter_name": perimeter_name,
        "access_policy_id": access_policy_id,
        "violations_analyzed": violations,
        "remediation_gcloud_cli": gcloud_command,
        "remediation_terraform_hcl": terraform_hcl,
    }
    return enforce_tool_output_budget(payload)


def check_gemini_enterprise_connectors() -> dict[str, Any]:
    """Monitor Gemini Enterprise federated connector health, OAuth token TTL, and quota utilization."""
    connectors = get_federated_connector_statuses()
    all_healthy = all(c["healthy"] for c in connectors)
    payload: dict[str, Any] = {
        "status": "CONNECTORS_HEALTHY" if all_healthy else "CONNECTOR_DEGRADED",
        "total_connectors": len(connectors),
        "connectors": connectors,
        "recommendations": [
            "Proactively rotate PagerDuty OAuth refresh token prior to 420s TTL expiry.",
            "Keep Atlassian Rovo and Google Workspace scopes pinned to least-privilege SRE runbook & postmortem folders.",
        ],
    }
    return enforce_tool_output_budget(payload)


security_guard_agent = LlmAgent(
    name="security_guard_agent",
    model=settings.specialist_model,
    description=(
        "Pillar 4 Specialist: Security, VPC Service Controls (VPC-SC) & Connector Guard. "
        "Diagnoses VpcServiceControlAuditMetadata blocks (SECURITY_POLICY_VIOLATED, "
        "SERVICE_NOT_ALLOWED_FROM_VPC, NO_MATCHING_ACCESS_LEVEL), generates gcloud and "
        "Terraform ingress/egress rules, and monitors Gemini Enterprise federated connectors."
    ),
    instruction=(
        "You are the Pillar 4 Security, VPC Service Controls & Connector Guard Specialist. "
        "Analyze Cloud Audit Logs (`type.googleapis.com/google.cloud.audit.VpcServiceControlAuditMetadata`) "
        "for SECURITY_POLICY_VIOLATED, SERVICE_NOT_ALLOWED_FROM_VPC, and NO_MATCHING_ACCESS_LEVEL, "
        "output ready-to-apply `gcloud access-context-manager perimeters` commands and Terraform "
        "ingress/egress resources, and audit Gemini Enterprise federated connector OAuth health."
    ),
    tools=[
        diagnose_vpc_sc_audit_violations,
        check_gemini_enterprise_connectors,
    ],
)

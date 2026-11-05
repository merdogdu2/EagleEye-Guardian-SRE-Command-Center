# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Thin composition root (< 100 lines) for the EagleEye Guardian SRE multi-agent system."""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps import App, ResumabilityConfig
from google.adk.apps.app import EventsCompactionConfig

from app.core.config import settings
from app.core.guardrails import (
    BigQueryAgentAnalyticsPlugin,
    SafetyAndA2UIPlugin,
    after_model_callback,
    before_model_call,
)
from app.pillars import (
    capacity_shield_agent,
    database_reliability_agent,
    incident_triage_agent,
    security_guard_agent,
)

root_agent = LlmAgent(
    name="eagleeye_guardian_root",
    model=settings.router_model,
    description=(
        "EagleEye Guardian SRE & Cloud Operations Router for global retail loyalty and POS "
        "transaction platforms (<250ms p99 SLA) on Google Cloud Gemini Enterprise."
    ),
    instruction=(
        "You are EagleEye Guardian, the autonomous SRE Command Router for a global retail "
        "loyalty and POS platform (<250ms p99 SLA across europe-west2, europe-west1, us-east1, "
        "us-east4, australia-southeast1, australia-southeast2). Route requests accurately to:\n"
        "1. `incident_triage_agent`: POS latency SLA breaches, ZONE_RESOURCE_POOL_EXHAUSTED, "
        "Atlassian Rovo (Jira/Confluence) grounding, and Google Workspace postmortems.\n"
        "2. `capacity_shield_agent`: Legacy N1 exit to Gen 3/4 (C4, N4, C3, C3D), Idle Standby "
        "Reservation vs. CUD FinOps, and G4 (NVIDIA RTX PRO 6000) GPU placement advisor.\n"
        "3. `database_reliability_agent`: Zonal SSD PD to Regional Hyperdisk Balanced HA "
        "(640k IOPS, 20,000 MiB/s, RPO=0, <2.5m RTO, torn-write protection, Snapshot Recycle Bin) "
        "and Cloud Spanner transactional load testing.\n"
        "4. `security_guard_agent`: VPC Service Controls (VpcServiceControlAuditMetadata) "
        "diagnostics, gcloud/Terraform rules, and Gemini Enterprise federated connector health."
    ),
    sub_agents=[
        incident_triage_agent,
        capacity_shield_agent,
        database_reliability_agent,
        security_guard_agent,
    ],
    before_model_callback=before_model_call,
    after_model_callback=after_model_callback,
)

app = App(
    name="eagleeye_guardian_sre",
    root_agent=root_agent,
    context_cache_config=ContextCacheConfig(
        cache_intervals=10,
        ttl_seconds=1800,
        min_tokens=2048,
    ),
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=12,
        overlap_size=2,
    ),
    resumability_config=ResumabilityConfig(is_resumable=True),
    plugins=[
        BigQueryAgentAnalyticsPlugin(
            project_id=settings.project_id,
            dataset_id=settings.bq_analytics_dataset,
            table_id=settings.bq_analytics_table,
        ),
        SafetyAndA2UIPlugin(),
    ],
)

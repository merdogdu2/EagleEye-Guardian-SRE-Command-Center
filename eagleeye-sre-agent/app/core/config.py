# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Environment-backed configuration settings for EagleEye Guardian."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

GLOBAL_RETAIL_REGIONS: tuple[str, ...] = (
    "europe-west2",
    "europe-west1",
    "us-east1",
    "us-east4",
    "australia-southeast1",
    "australia-southeast2",
)

POS_P99_SLA_MS: float = 250.0
MAX_TOOL_OUTPUT_BYTES: int = 16_384  # 16 KB strict tool output budget
AGENTS_MD_MAX_BYTES: int = 8_192  # 8 KB strict AGENTS.md budget


@dataclass(frozen=True)
class SREAgentSettings:
    """Immutable runtime settings populated from environment variables."""

    project_id: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
    )
    location: str = field(
        default_factory=lambda: os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    )
    router_model: str = field(
        default_factory=lambda: os.environ.get("SRE_ROUTER_MODEL", "gemini-2.5-flash")
    )
    specialist_model: str = field(
        default_factory=lambda: os.environ.get("SRE_SPECIALIST_MODEL", "gemini-2.5-pro")
    )
    iframe_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "A2UI_IFRAME_BASE_URL",
            "https://eagleeye-sre-command-center.example.com",
        )
    )
    bq_analytics_dataset: str = field(
        default_factory=lambda: os.environ.get("BQ_ANALYTICS_DATASET", "sre_agent_analytics")
    )
    bq_analytics_table: str = field(
        default_factory=lambda: os.environ.get("BQ_ANALYTICS_TABLE", "agent_events")
    )
    pos_p99_sla_ms: float = POS_P99_SLA_MS
    retail_regions: tuple[str, ...] = GLOBAL_RETAIL_REGIONS


settings = SREAgentSettings()

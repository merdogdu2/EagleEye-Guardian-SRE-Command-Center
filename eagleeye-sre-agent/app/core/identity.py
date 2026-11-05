# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Identity, OAuth Federated Connector context, and RBAC validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FederatedConnectorStatus:
    """Health and OAuth state of a Gemini Enterprise federated connector."""

    connector_id: str
    display_name: str
    provider: str
    oauth_status: str
    token_ttl_seconds: int
    quota_used_pct: float
    last_sync_utc: str
    scopes: list[str]
    healthy: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "display_name": self.display_name,
            "provider": self.provider,
            "oauth_status": self.oauth_status,
            "token_ttl_seconds": self.token_ttl_seconds,
            "quota_used_pct": round(self.quota_used_pct, 2),
            "last_sync_utc": self.last_sync_utc,
            "scopes": list(self.scopes),
            "healthy": self.healthy,
        }


DEFAULT_CONNECTORS: tuple[FederatedConnectorStatus, ...] = (
    FederatedConnectorStatus(
        connector_id="conn-atlassian-rovo-prod",
        display_name="Atlassian Rovo (Jira & Confluence SRE Runbooks)",
        provider="Atlassian Cloud",
        oauth_status="VALID_TOKEN",
        token_ttl_seconds=3420,
        quota_used_pct=38.4,
        last_sync_utc="2026-11-05T08:45:00Z",
        scopes=["read:jira-work", "write:jira-work", "read:confluence-content.all"],
        healthy=True,
    ),
    FederatedConnectorStatus(
        connector_id="conn-google-workspace-prod",
        display_name="Google Workspace (Docs, Slides & Sheets Postmortem Studio)",
        provider="Google Workspace",
        oauth_status="VALID_TOKEN",
        token_ttl_seconds=3590,
        quota_used_pct=21.5,
        last_sync_utc="2026-11-05T08:47:00Z",
        scopes=[
            "https://www.googleapis.com/auth/documents",
            "https://www.googleapis.com/auth/presentations",
            "https://www.googleapis.com/auth/spreadsheets",
        ],
        healthy=True,
    ),
    FederatedConnectorStatus(
        connector_id="conn-pagerduty-incident-bridge",
        display_name="PagerDuty On-Call Escalation Connector",
        provider="PagerDuty",
        oauth_status="REFRESH_REQUIRED_SOON",
        token_ttl_seconds=420,
        quota_used_pct=74.0,
        last_sync_utc="2026-11-05T08:40:00Z",
        scopes=["incidents:read", "incidents:write", "oncalls:read"],
        healthy=True,
    ),
)


def get_federated_connector_statuses() -> list[dict[str, Any]]:
    """Return status cards for all configured Gemini Enterprise federated connectors."""
    return [c.to_dict() for c in DEFAULT_CONNECTORS]

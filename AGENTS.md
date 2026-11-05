# EagleEye Guardian — Coding Agent Contract (`AGENTS.md`)

> **License**: Apache 2.0 | **Budget**: `< 8 KB` (enforced by `tests/unit/test_architecture_and_guardrails.py`).

## 1. System Overview & Architectural Boundaries
**EagleEye Guardian** is a production-grade SRE & Cloud Operations multi-agent system built for a high-concurrency global retail loyalty and POS transaction platform (`<250ms` p99 SLA across `europe-west2`, `europe-west1`, `us-east1`, `us-east4`, `australia-southeast1`, `australia-southeast2`) on **Google Cloud Gemini Enterprise**.

- **Thin Composition Root (`eagleeye-sre-agent/app/agent.py`)**: Must remain **strictly `< 100` lines**. Wires `root_agent` (`gemini-2.5-flash`) to four specialist sub-agents (`gemini-2.5-pro`) inside an ADK `App` with `ContextCacheConfig`, `EventsCompactionConfig`, `ResumabilityConfig`, `BigQueryAgentAnalyticsPlugin`, and `SafetyAndA2UIPlugin`.
- **Four Specialist Pillars (`eagleeye-sre-agent/app/pillars/`)**:
  1. `pillar1_incident.py` (`incident_triage_agent`): POS coupon/wallet p99 latency correlation, `ZONE_RESOURCE_POOL_EXHAUSTED` detection, Atlassian Rovo (Jira/Confluence) & Google Workspace (Docs/Slides/Sheets) 1-click postmortem generation.
  2. `pillar2_capacity.py` (`capacity_shield_agent`): Legacy `N1` exit to Gen 3/4 (`C4`, `N4`, `C3`, `C3D`), Idle Standby Compute Reservation vs. CUD FinOps audit, and **G4 GPU Placement Advisor** (NVIDIA RTX PRO 6000: Spot `g4-standard-384` vs. DWS Flex-start vs. cross-region spillover).
  3. `pillar3_database.py` (`database_reliability_agent`): Track 1 — Zonal SSD PD (`100k` IOPS, `1,200 MiB/s`) to **Regional Hyperdisk Balanced HA** (`640k` IOPS, `20,000 MiB/s`, `RPO=0`, `<2.5m` RTO, torn-write protection, 1x/4h dynamic scaling, Snapshot Recycle Bin). Track 2 — Cloud Spanner migration & load testing (`LongRunningFunctionTool`) with split/hot-key analysis.
  4. `pillar4_security.py` (`security_guard_agent`): VPC Service Controls (`VpcServiceControlAuditMetadata`) parser for `SECURITY_POLICY_VIOLATED`, `SERVICE_NOT_ALLOWED_FROM_VPC`, `NO_MATCHING_ACCESS_LEVEL`, generating `gcloud` and Terraform ingress/egress policies + Gemini Enterprise federated connector health checks.

## 2. Public Repository & Security Hygiene (Zero-Leak Gate)
- **Zero Secrets or Internal Identifiers**: Never commit internal URLs, internal shortlinks, real customer GCP project IDs/numbers, organization IDs, internal model codenames, or employee emails.
- **Environment Variables Only**: Always read `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `SRE_ROUTER_MODEL`, `SRE_SPECIALIST_MODEL`, and `A2UI_IFRAME_BASE_URL` via `app/core/config.py`.
- **Tool Payload Cap**: Every tool output MUST be `<= 16,384` bytes (`16 KB`) to prevent context window bloat.

## 3. Ten Mandatory A2UI v0.9 Guardrails
All A2UI v0.9 surfaces (`app/core/a2ui/`) are wrapped in `Part(inline_data=Blob(mime_type="text/plain", data=b"<a2a_datapart_json>" + json_bytes + b"</a2a_datapart_json>"), part_metadata={"mimeType": "application/json+a2ui"})` with catalog `"https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"`:

1. **No `h6` variant**: Allowed `MaterialText.usageHint` values are `h1`–`h5`, `subtitle1`, `subtitle2`, `body1`, `body2`, `caption`, `body`.
2. **No Markdown headings in `MaterialText`**: Never start `text` with `#` when `usageHint` is set.
3. **Single `Canvas` root column**: Every `Canvas` root must have a single child ID pointing to a `MaterialColumn` with `justify: "start"`.
4. **Clean `RichTable` spec & numbers**: `tableData.spec` MUST be `{}` and numeric cells coerced to raw `int`/`float` (no commas, currency symbols, `NaN`, or `inf`).
5. **Flat adjacency list**: `updateComponents.components` must be a flat list with `"id": "root"` and string ID arrays in `children`.
6. **Data-model bindings for complex objects**: Bind `VegaChart.spec` and `RichTable.tableData` via `updateDataModel` paths (`{"path": "/..."}`).
7. **String-coerced numeric bindings**: Wrap numeric paths inside `MaterialText` using `formatNumber` or `formatString` with `"returnType": "string"`.
8. **Prompt in button context**: Every interactive `MaterialButton` `action.event.context` MUST include a human-readable `"prompt"` string.
9. **History sanitization (`before_model_call`)**: Replace prior-turn `<a2a_datapart_json>` blobs with concise text summaries so the LLM never echoes raw A2UI JSON in prose.
10. **Graceful UI fallback (`after_model_callback`)**: Wrap surface construction in `try/except` so errors degrade cleanly to text.

## 4. Verification Commands
Run all four gates before completing any change:
```bash
cd eagleeye-sre-agent && CLOUDSDK_CONFIG=/nonexistent uv run pytest tests/unit -v
cd eagleeye-sre-agent && uv run python scripts/validate_a2ui.py --self-test
cd eagleeye-sre-agent && uv run ruff check . && uv run ruff format --check .
cd a2ui-iframe && npm install && npm run build
```

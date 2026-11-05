# EagleEye Guardian — Autonomous SRE & Cloud Operations Platform

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![ADK](https://img.shields.io/badge/Google_ADK-Multi--Agent-4285F4)](https://google.github.io/adk-docs/)
[![A2UI](https://img.shields.io/badge/A2UI-v0.9_Composite_Catalog-34A853)](#a2ui-v09-architecture)
[![React 19](https://img.shields.io/badge/React_19-Vite_6_Stateless_Canvas-61DAFB)](#stateless-react-19-sre-command-center)

**EagleEye Guardian** is a production-grade, full-stack SRE & Cloud Operations multi-agent system designed for a global high-concurrency retail loyalty, coupon redemption, and Point-of-Sale (POS) transaction platform (`<250ms` p99 SLA across `europe-west2`, `europe-west1`, `us-east1`, `us-east4`, `australia-southeast1`, and `australia-southeast2`) running on **Google Cloud Gemini Enterprise**.

---

## 1. Multi-Agent Architecture

### 1.1 Executive System Context & Global Retail Footprint

```mermaid
flowchart LR
    classDef actor fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#f8fafc
    classDef ge fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#e0e7ff
    classDef adk fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ecfdf5
    classDef gcp fill:#172554,stroke:#60a5fa,stroke-width:2px,color:#eff6ff
    classDef conn fill:#451a03,stroke:#fbbf24,stroke-width:2px,color:#fef3c7

    SRE["SRE / Platform Engineer
    • On-Call Incident Commander
    • FinOps & Capacity Planner"]:::actor

    subgraph GE["Google Cloud Gemini Enterprise"]
        Chat["Conversational Assistant
        • Inline A2UI v0.9 MaterialCards
        • Stepper + VegaChart + HITL Gate"]:::ge
        Canvas["Right-Hand Side-Panel Canvas
        • Native Looker Studio RichTable
        • React 19 SRE Command Center IFrame"]:::ge
    end

    subgraph Runtime["Vertex AI Agent Engine & Cloud Run A2A"]
        App["EagleEye Guardian ADK App
        • SafetyAndA2UIPlugin (10 Guardrails)
        • BigQueryAgentAnalyticsPlugin
        • ContextCache & EventsCompaction"]:::adk
    end

    subgraph Fleet["6 Global Retail POS Regions (<250ms p99 SLA)"]
        EU["EMEA Retail Footprint
        • europe-west2 (London)
        • europe-west1 (Belgium)"]:::gcp
        US["Americas Retail Footprint
        • us-east1 (South Carolina)
        • us-east4 (Northern Virginia)"]:::gcp
        APAC["APAC Retail Footprint
        • australia-southeast1 (Sydney)
        • australia-southeast2 (Melbourne)"]:::gcp
    end

    subgraph Connectors["Enterprise Federated Connectors"]
        Rovo["Atlassian Rovo
        • Jira Incident Tickets
        • Confluence SRE Runbooks"]:::conn
        GWS["Google Workspace
        • Docs Blameless Postmortems
        • Slides Exec Decks & Sheets"]:::conn
    end

    SRE <==>|"Natural Language &
    Interactive UI Clicks"| GE
    Chat & Canvas <==>|"A2A JSON-RPC +
    Part(application/json+a2ui)"| App
    App <==>|"Cloud Monitoring, Compute,
    Hyperdisk HA, Spanner, VPC-SC"| EU & US & APAC
    App <==>|"OAuth 2.0 Federated
    Grounding & Action Execution"| Rovo & GWS
```

---

### 1.2 ADK Multi-Agent Orchestration & Specialist Pillar Topology

```mermaid
flowchart TB
    classDef plugin fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#e0e7ff
    classDef router fill:#172554,stroke:#38bdf8,stroke-width:2.5px,color:#f0f9ff
    classDef pillar fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ecfdf5
    classDef tool fill:#0f172a,stroke:#64748b,stroke-width:1.5px,color:#e2e8f0

    subgraph Ingress["1. Inbound Request & History Sanitization Pipeline"]
        InHook["SafetyAndA2UIPlugin.before_model_call
        • Intercepts inbound a2ui_action payloads deterministically
        • Strips prior-turn <a2a_datapart_json> into concise text summaries"]:::plugin
        CacheCfg["ADK Runtime State & Telemetry
        • ContextCacheConfig (TTL 1800s, min 2048 tokens)
        • EventsCompactionConfig (interval 12, overlap 2)
        • ResumabilityConfig + BigQueryAgentAnalyticsPlugin"]:::plugin
    end

    Router["2. eagleeye_guardian_root (gemini-2.5-flash)
    Low-Latency Intent Classifier & Multi-Pillar Coordinator"]:::router

    subgraph Pillars["3. Four Domain Specialist Sub-Agents (gemini-2.5-pro)"]
        direction LR

        subgraph Col1["Pillar 1: Incident & Postmortem"]
            P1["incident_triage_agent"]:::pillar
            T1A["correlate_pos_incident_telemetry
            • <250ms p99 POS SLA monitor
            • ZONE_RESOURCE_POOL_EXHAUSTED"]:::tool
            T1B["ground_and_create_rovo_incident
            • Confluence runbook grounding
            • P1 Jira ticket creation"]:::tool
            T1C["generate_workspace_blameless_postmortem
            • 1-click Docs, Slides & Sheets"]:::tool
            P1 --> T1A & T1B & T1C
        end

        subgraph Col2["Pillar 2: Capacity & GPU Shield"]
            P2["capacity_shield_agent"]:::pillar
            T2A["audit_bfcm_n1_exit_and_headroom
            • Legacy N1 -> C4/N4/C3/C3D
            • Cross-family BFCM spillover"]:::tool
            T2B["audit_idle_reservations_vs_cuds
            • Retires warm-standby VMs
            • 3-yr Flexible CUD optimization"]:::tool
            T2C["advise_g4_gpu_placement
            • NVIDIA RTX PRO 6000 (g4-standard-384)
            • Spot vs. DWS Flex-start (<=7d)"]:::tool
            P2 --> T2A & T2B & T2C
        end

        subgraph Col3["Pillar 3: Database & Storage"]
            P3["database_reliability_agent"]:::pillar
            T3A["model_hyperdisk_balanced_ha_migration
            • 640k IOPS / 20,000 MiB/s
            • RPO=0, <2.5m RTO, Torn-Write Off"]:::tool
            T3B["optimize_snapshot_recycle_bin
            • 72h immutable ransomware guard
            • Delta-chain FinOps reclamation"]:::tool
            T3C["spanner_load_test_long_running_tool
            • LongRunningFunctionTool (150k+ QPS)
            • Split & hot-key diagnostics"]:::tool
            P3 --> T3A & T3B & T3C
        end

        subgraph Col4["Pillar 4: Security & VPC-SC"]
            P4["security_guard_agent"]:::pillar
            T4A["diagnose_vpc_sc_audit_violations
            • VpcServiceControlAuditMetadata
            • gcloud + Terraform HCL generator"]:::tool
            T4B["check_gemini_enterprise_connectors
            • OAuth token TTL & scope audit
            • Data-source quota guard"]:::tool
            P4 --> T4A & T4B
        end
    end

    subgraph Egress["4. Outbound Budget Enforcement & A2UI v0.9 Packaging"]
        ToolCap["SafetyAndA2UIPlugin.after_tool_callback
        • Enforces strict <= 16,384 byte (16 KB) JSON payload ceiling"]:::plugin
        OutHook["SafetyAndA2UIPlugin.after_model_callback
        • Validates all 10 mandatory A2UI v0.9 rules
        • Wraps <a2a_datapart_json> with try/except graceful text fallback"]:::plugin
    end

    InHook --> Router
    CacheCfg -.-> Router
    Router ==> P1 & P2 & P3 & P4
    Col1 & Col2 & Col3 & Col4 ==> ToolCap
    ToolCap ==> OutHook
```

---

### 1.3 A2UI v0.9 Wire Protocol, Stateless DEFLATE Hydration & `postMessage` Bridge

```mermaid
flowchart LR
    classDef py fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ecfdf5
    classDef wire fill:#3b0764,stroke:#c084fc,stroke-width:2px,color:#faf5ff
    classDef react fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#f0f9ff

    subgraph Backend["Python ADK A2UI v0.9 Engine (app/core/a2ui/)"]
        Builder["Surface Builders (surfaces.py)
        • createSurface (composite catalog)
        • updateDataModel (/chartSpec, /fleetTableData)
        • updateComponents (flat adjacency list)"]:::py
        CodecPy["Raw DEFLATE State Encoder (primitives.py)
        • zlib.compressobj(wbits=-15)
        • URL-safe Base64 -> #s=z.<base64url>"]:::py
        ActionPy["Deterministic Action Dispatcher (actions.py)
        • Parses inbound a2ui_action JSON
        • Emits in-place updateComponents receipt"]:::py
    end

    subgraph Wire["Gemini Enterprise A2A Stream"]
        PartEnv["google.genai.types.Part
        • inline_data: <a2a_datapart_json>[...]</a2a_datapart_json>
        • part_metadata: mimeType = application/json+a2ui"]:::wire
        PostMsg["Browser postMessage Bridge
        • type: a2ui_action
        • action: scale_hyperdisk_iops | confirm_hitl_execution
        • data: { prompt, surfaceId, ...payload }"]:::wire
    end

    subgraph Frontend["Stateless React 19 + Vite 6 Workbench (a2ui-iframe/)"]
        Hydrate["Zero-Privilege URL Hash Inflator (codec.ts)
        • Reads window.location.hash (#s=z.*)
        • DecompressionStream('deflate-raw')
        • Standalone Demo Dataset fallback"]:::react
        Tabs["Four Interactive SRE Workbench Tabs (App.tsx)
        • Tab 1: BFCM N1 Exit & G4 GPU Advisor
        • Tab 2: Hyperdisk Balanced HA FinOps Sliders
        • Tab 3: Cloud Spanner Split & Hot-Key Visualizer
        • Tab 4: VPC-SC Terraform/gcloud & OAuth Guard"]:::react
    end

    Builder --> PartEnv
    CodecPy -->|"origin=REPLACE_WITH_PARENT_ORIGIN#s=z.*"| PartEnv
    PartEnv ==> Hydrate
    Hydrate --> Tabs
    Tabs ==>|"window.parent.postMessage(...)"| PostMsg
    PostMsg ==> ActionPy
    ActionPy -->|"In-place surfaceId update"| Builder
```

---

### 1.4 Incident-to-Remediation Sequence & In-Place HITL State Machine

```mermaid
sequenceDiagram
    autonumber
    actor SRE as SRE Commander
    participant GE as Gemini Enterprise UI
    participant Plugin as SafetyAndA2UIPlugin
    participant Router as eagleeye_guardian_root
    participant Pillars as Specialist Pillars (1-4)
    participant IFrame as React 19 a2ui-iframe

    rect rgb(15, 23, 42)
        Note over SRE,Pillars: Phase 1 — Real-Time POS SLA Triage & Multi-Pillar Correlation
        SRE->>GE: "europe-west2 POS p99 jumped to 682ms with ZONE_RESOURCE_POOL_EXHAUSTED"
        GE->>Plugin: LlmRequest (with prior-turn history)
        Plugin->>Plugin: before_model_call sanitizes prior A2UI blobs to text summaries
        Plugin->>Router: Forward clean LlmRequest
        Router->>Pillars: Delegate to incident_triage_agent & database_reliability_agent
        Pillars-->>Plugin: Telemetry JSON (<= 16 KB cap verified by after_tool_callback)
        Plugin-->>GE: Prose RCA + Part(application/json+a2ui) [Incident Card + IFrame Canvas]
    end

    rect rgb(30, 27, 75)
        Note over GE,IFrame: Phase 2 — Zero-Privilege URL-Hash DEFLATE Hydration
        GE->>IFrame: Load IFrameUrl (?origin=...#s=z.<deflate-raw-base64url>)
        IFrame->>IFrame: DecompressionStream('deflate-raw') hydrates 4 SRE Workbench Tabs
        SRE->>IFrame: Tune Hyperdisk Balanced HA sliders (320k IOPS, 12,000 MiB/s, Torn-Write Off)
        IFrame->>GE: window.parent.postMessage({ type: "a2ui_action", action: "scale_hyperdisk_iops", data: { prompt } })
    end

    rect rgb(6, 78, 59)
        Note over GE,Plugin: Phase 3 — Human-in-the-Loop (HITL) Gate & In-Place Receipt Update
        GE->>Plugin: Forward inbound a2ui_action event
        Plugin-->>GE: Render HITL Confirmation Gate (surfaceId: "sre-hitl-confirmation-gate")
        SRE->>GE: Verify validation checks & click "Confirm & Execute Change"
        GE->>Plugin: event: confirm_hitl_execution (surfaceId: "sre-hitl-confirmation-gate")
        Plugin-->>GE: Emit updateComponents on SAME surfaceId -> Immutable Execution Receipt
    end
```

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Detected: POS p99 > 250ms Alert
    Detected --> Correlated: correlate_pos_incident_telemetry()\nZONE_RESOURCE_POOL_EXHAUSTED + 100k IOPS Cap
    Correlated --> HITL_Gate_Open: scale_hyperdisk_iops\n(sre-hitl-confirmation-gate)
    HITL_Gate_Open --> Mitigating: confirm_hitl_execution\nIn-Place Receipt (320k IOPS, RPO=0)
    HITL_Gate_Open --> Correlated: cancel_hitl_execution\nIn-Place Cancellation Receipt
    Mitigating --> Resolved: C4/N4 Spillover Complete\nPOS p99 = 188ms (<250ms SLA)
    Resolved --> [*]: 1-Click Rovo Jira + Workspace Postmortem
```

---

## 2. Four SRE Domain Pillars

| Pillar | Sub-Agent | Core Capabilities |
| :--- | :--- | :--- |
| **1. Incident Triage, POS Latency & Postmortem** | `incident_triage_agent` | Monitors `<250ms` p99 retail POS coupon/loyalty APIs across 6 global regions; correlates latency spikes with `ZONE_RESOURCE_POOL_EXHAUSTED` and storage IOPS saturation; integrates with **Atlassian Rovo** (Jira/Confluence) and **Google Workspace** (Docs/Slides/Sheets) for 1-click blameless postmortems. |
| **2. Multi-Region Capacity Shield & GPU Placement** | `capacity_shield_agent` | Tracks legacy 1st-Gen `N1` VM migration to Gen 3/4 (`C4`, `N4`, `C3`, `C3D`) ahead of BFCM peaks; audits **Idle Standby Compute Reservations** vs. CUDs; includes the **G4 GPU Placement Advisor** (NVIDIA RTX PRO 6000) comparing **Spot VMs (`g4-standard-384`)**, **DWS Flex-start** (up to 7 days), and cross-region spillover. |
| **3. Database & Storage Reliability** | `database_reliability_agent` | **Track 1**: Modernizes 50+ TB MySQL clusters from Zonal SSD PD (`100k` IOPS, `1,200 MiB/s`) to **Regional Hyperdisk Balanced HA** (`640k` IOPS, `20,000 MiB/s`, `RPO=0`, `<2.5m` RTO, torn-write protection disabling MySQL doublewrite buffer, 1x/4h dynamic scaling, Snapshot Recycle Bin). **Track 2**: Cloud Spanner transactional ledger load testing (`LongRunningFunctionTool`) with split-boundary & hot-key diagnostics. |
| **4. Security, VPC-SC & Connector Guard** | `security_guard_agent` | Parses `VpcServiceControlAuditMetadata` logs (`SECURITY_POLICY_VIOLATED`, `SERVICE_NOT_ALLOWED_FROM_VPC`, `NO_MATCHING_ACCESS_LEVEL`), emits ready-to-apply `gcloud access-context-manager perimeters` and Terraform HCL patches, and monitors Gemini Enterprise federated connector health. |

---

## 3. A2UI v0.9 Architecture & Guardrails

EagleEye Guardian emits rich interactive surfaces natively rendered by Gemini Enterprise using the `v0.9` composite catalog (`https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json`):

- **Wire Format**: `Part(inline_data=Blob(mime_type="text/plain", data=b"<a2a_datapart_json>" + json_bytes + b"</a2a_datapart_json>"), part_metadata={"mimeType": "application/json+a2ui"})`
- **Four Core Surfaces**:
  1. **Inline Incident & SLO Triage Card (`MaterialCard`)**: `Stepper` (`Detected → Correlated → Mitigating → Resolved`), `VegaChart` bound at `/chartSpec`, and `MaterialButton` actions.
  2. **Inline HITL Confirmation Gate (`MaterialCard`)**: Pre-filled `MaterialSelect` / `MaterialInput` with client-side validation `checks`, updating **in-place** (`updateComponents` on the same `surfaceId`) into an immutable execution receipt.
  3. **Native Side-Panel Fleet & FinOps Explorer (`Canvas` + `RichTable`)**: Multi-region fleet metrics with clean `tableData.spec = {}` and raw numeric cells.
  4. **Stateless React 19 SRE Command Center (`Canvas` + `IFrameUrl`)**: Hydrated via `#s=z.<deflate-raw-base64url>` with zero backend database dependencies.

---

## 4. Stateless React 19 SRE Command Center (`a2ui-iframe/`)

The `a2ui-iframe/` workbench runs inside the Gemini Enterprise right-hand `Canvas` panel:
- **Zero-Privilege URL Hash Hydration**: Inflates `#s=z.<base64url>` in-browser via `DecompressionStream('deflate-raw')` and falls back to a built-in realistic retail SRE telemetry dataset when opened standalone.
- **Four Interactive Workbench Tabs**:
  1. **BFCM Capacity & N1 Exit Matrix** (including the interactive **G4 GPU Placement Advisor**).
  2. **Hyperdisk Balanced HA & Reservation FinOps Calculator** (live sliders up to `640k` IOPS and `20,000 MiB/s`).
  3. **Cloud Spanner Load-Test & Split Visualizer** (QPS vs. p99 latency, hot-key detection, interleaved schema advice).
  4. **VPC-SC Perimeter & Connector Guard** (1-click Terraform & `gcloud` rule generator + connector OAuth health).
- **Bidirectional `a2ui_action` Bridge**: Dispatches `window.parent.postMessage({ type: "a2ui_action", action, data: { prompt, ...payload } }, targetOrigin)` back to the ADK agent.

---

## 5. Quickstart & Verification

### Run Python Unit Tests, A2UI Validator, and Ruff Linter
```bash
cd eagleeye-sre-agent
CLOUDSDK_CONFIG=/nonexistent uv run pytest tests/unit -v
uv run python scripts/validate_a2ui.py --self-test
uv run ruff check . && uv run ruff format --check .
```

### Build Stateless React 19 `a2ui-iframe` Workbench
```bash
cd a2ui-iframe
npm install
npm run build
```

---

## 6. Copy-Paste Demo Prompt Playbook

### Pillar 1 — Retail POS Latency Triage & 1-Click Blameless Postmortem
```text
Urgent: europe-west2 POS coupon redemption p99 latency jumped to 680ms (SLA <250ms) and we see ZONE_RESOURCE_POOL_EXHAUSTED in europe-west2-b. Correlate Cloud Monitoring metrics with storage IOPS, open the Incident Triage Card, and prepare a blameless postmortem via Atlassian Rovo and Google Workspace.
```

### Pillar 2 — BFCM Legacy N1 Exit, Idle Reservation Audit & G4 GPU Advisor
```text
Audit our BFCM readiness across europe-west2, us-east1, and australia-southeast1: show remaining N1 VMs to migrate to C4/N4, calculate savings from retiring idle standby reservations, and recommend where to place our 64-GPU NVIDIA RTX PRO 6000 (G4) visual-search training workload using Spot vs. DWS Flex-start.
```

### Pillar 3 — MySQL Hyperdisk Balanced HA Modernization & Spanner Load Test
```text
Model migrating our 64 TiB loyalty MySQL cluster from Zonal SSD PD to Regional Hyperdisk Balanced HA (320,000 IOPS, 12,000 MiB/s, torn-write protection enabled), and trigger a 150,000 QPS Cloud Spanner ledger load test to check for hot keys.
```

### Pillar 4 — VPC Service Controls Violation Diagnostics & Connector Guard
```text
Diagnose the recent VPC Service Controls SECURITY_POLICY_VIOLATED and NO_MATCHING_ACCESS_LEVEL blocks on bigquery.googleapis.com and storage.googleapis.com, generate the gcloud and Terraform ingress/egress remediation rules, and check our Gemini Enterprise Atlassian Rovo and Google Workspace connector health.
```

---

## 7. Gemini Enterprise Registration Guide

1. Deploy `a2ui-iframe/` to Cloud Run (`--allow-unauthenticated`, served via `nginx.conf` with no `X-Frame-Options` and `Cache-Control: no-store`).
2. Deploy `eagleeye-sre-agent/` to Vertex AI Agent Engine with environment variables defined in `.env.example`.
3. Register the Agent Engine reasoning engine resource in **Google Cloud Gemini Enterprise** with A2UI v0.9 composite catalog enabled and Federated Connectors linked for Atlassian Rovo and Google Workspace.

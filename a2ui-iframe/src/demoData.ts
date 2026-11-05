// Copyright 2026 EagleEye Guardian Contributors
// SPDX-License-Identifier: Apache-2.0

import { WorkbenchHydratedState } from './types';

export const DEFAULT_WORKBENCH_STATE: WorkbenchHydratedState = {
  activeTab: 'capacity',
  slaTargetMs: 250,
  incident: {
    id: 'INC-2026-8841',
    region: 'europe-west2',
    zone: 'europe-west2-b',
    p99Ms: 682.4,
    status: 'Correlated (ZONE_RESOURCE_POOL_EXHAUSTED + Zonal SSD PD 100k IOPS Cap)',
  },
  hyperdiskDefaults: {
    capacityTib: 64,
    iops: 320000,
    throughputMib: 12000,
    discountPct: 28,
    retiredStandbyVms: 16,
    tornWriteProtection: true,
  },
  regionsMatrix: [
    {
      region: 'europe-west2',
      legacyN1Vms: 42,
      modernGen34Vms: 180,
      targetFamilies: ['c4-standard-32', 'n4-standard-32', 'c3-standard-44'],
      bfcmHeadroomPct: 34.5,
      idleStandbyVms: 16,
      posP99Ms: 682.4,
      exhaustedZone: 'europe-west2-b',
    },
    {
      region: 'europe-west1',
      legacyN1Vms: 18,
      modernGen34Vms: 140,
      targetFamilies: ['c4-standard-32', 'n4-standard-32', 'c3d-standard-30'],
      bfcmHeadroomPct: 46.0,
      idleStandbyVms: 12,
      posP99Ms: 174.2,
      exhaustedZone: null,
    },
    {
      region: 'us-east1',
      legacyN1Vms: 55,
      modernGen34Vms: 220,
      targetFamilies: ['c4-standard-48', 'n4-highmem-32', 'c3-standard-44'],
      bfcmHeadroomPct: 31.0,
      idleStandbyVms: 20,
      posP99Ms: 241.8,
      exhaustedZone: 'us-east1-c',
    },
    {
      region: 'us-east4',
      legacyN1Vms: 12,
      modernGen34Vms: 160,
      targetFamilies: ['c4-standard-32', 'n4-standard-32'],
      bfcmHeadroomPct: 52.0,
      idleStandbyVms: 8,
      posP99Ms: 152.0,
      exhaustedZone: null,
    },
    {
      region: 'australia-southeast1',
      legacyN1Vms: 24,
      modernGen34Vms: 96,
      targetFamilies: ['c4-standard-32', 'n4-standard-32', 'c3-standard-22'],
      bfcmHeadroomPct: 38.0,
      idleStandbyVms: 10,
      posP99Ms: 218.5,
      exhaustedZone: null,
    },
    {
      region: 'australia-southeast2',
      legacyN1Vms: 8,
      modernGen34Vms: 74,
      targetFamilies: ['n4-standard-32', 'c3-standard-22'],
      bfcmHeadroomPct: 54.0,
      idleStandbyVms: 6,
      posP99Ms: 161.3,
      exhaustedZone: null,
    },
  ],
  spannerSplits: [
    {
      splitId: 'split-shard-00..15',
      keyRange: 'ShardId=00..15 / LoyaltyWallets',
      qps: 42500,
      p99ReadMs: 6.1,
      p99WriteMs: 13.4,
      cpuUtilizationPct: 48,
      isHotKey: false,
      remediationNote: 'Balanced via FARM_FINGERPRINT(WalletId) prefix & interleaved child tables.',
    },
    {
      splitId: 'split-shard-16..31',
      keyRange: 'ShardId=16..31 / LoyaltyWallets',
      qps: 44100,
      p99ReadMs: 6.4,
      p99WriteMs: 13.9,
      cpuUtilizationPct: 51,
      isHotKey: false,
      remediationNote: 'Balanced parent-child co-location (LoyaltyWallets -> CouponRedemptions).',
    },
    {
      splitId: 'split-shard-32..47',
      keyRange: 'ShardId=32..47 / LoyaltyWallets',
      qps: 41800,
      p99ReadMs: 6.0,
      p99WriteMs: 13.1,
      cpuUtilizationPct: 47,
      isHotKey: false,
      remediationNote: 'Healthy multi-region quorum commit latency well below 250ms POS SLA.',
    },
    {
      splitId: 'split-hotkey-legacy-ts',
      keyRange: '2026-11-05T08:45:* / CouponRedemptionEvents',
      qps: 27600,
      p99ReadMs: 18.9,
      p99WriteMs: 42.8,
      cpuUtilizationPct: 89,
      isHotKey: true,
      remediationNote: 'Monotonic timestamp key detected: prepend bit-reversed ShardId and INTERLEAVE IN PARENT LoyaltyWallets.',
    },
  ],
  vpcViolations: [
    {
      violationId: 'VPCSC-2026-991',
      reason: 'SECURITY_POLICY_VIOLATED',
      targetService: 'bigquery.googleapis.com',
      methodName: 'google.cloud.bigquery.v2.JobService.InsertJob',
      principalEmail: 'sa-sre-analytics@your-gcp-project-id.iam.gserviceaccount.com',
      perimeter: 'sp_eagleeye_retail_prod',
      diagnosis: 'BigQuery Agent Analytics write stream blocked by missing egress rule to telemetry project.',
      gcloudCli:
        'gcloud access-context-manager perimeters update sp_eagleeye_retail_prod --policy=policy_retail_global_01 --set-egress-policies=egress_bq_analytics.yaml',
      terraformHcl: `resource "google_access_context_manager_service_perimeter_egress_policy" "bq_analytics_egress" {
  perimeter = "accessPolicies/policy_retail_global_01/servicePerimeters/sp_eagleeye_retail_prod"
  egress_from {
    identities = ["serviceAccount:sa-sre-analytics@your-gcp-project-id.iam.gserviceaccount.com"]
  }
  egress_to {
    resources = ["projects/\${var.analytics_project_number}"]
    operations {
      service_name = "bigquery.googleapis.com"
      method_selectors { method = "google.cloud.bigquery.v2.JobService.InsertJob" }
    }
  }
}`,
    },
    {
      violationId: 'VPCSC-2026-992',
      reason: 'SERVICE_NOT_ALLOWED_FROM_VPC',
      targetService: 'storage.googleapis.com',
      methodName: 'google.cloud.storage.ReadObject',
      principalEmail: 'sa-pos-ledger-sync@your-gcp-project-id.iam.gserviceaccount.com',
      perimeter: 'sp_eagleeye_retail_prod',
      diagnosis: 'GKE POS node pool in europe-west2 attempted Cloud Storage snapshot read over restricted VIP.',
      gcloudCli:
        'gcloud access-context-manager perimeters update sp_eagleeye_retail_prod --policy=policy_retail_global_01 --add-restricted-services=storage.googleapis.com --set-ingress-policies=ingress_gcs.yaml',
      terraformHcl: `resource "google_access_context_manager_service_perimeter_ingress_policy" "gcs_pos_ingress" {
  perimeter = "accessPolicies/policy_retail_global_01/servicePerimeters/sp_eagleeye_retail_prod"
  ingress_from {
    identities = ["serviceAccount:sa-pos-ledger-sync@your-gcp-project-id.iam.gserviceaccount.com"]
  }
  ingress_to {
    resources = ["projects/\${var.project_number}"]
    operations {
      service_name = "storage.googleapis.com"
      method_selectors { method = "*" }
    }
  }
}`,
    },
    {
      violationId: 'VPCSC-2026-993',
      reason: 'NO_MATCHING_ACCESS_LEVEL',
      targetService: 'discoveryengine.googleapis.com',
      methodName: 'google.cloud.discoveryengine.v1.ConversationalSearchService.AnswerQuery',
      principalEmail: 'sa-gemini-enterprise-connector@your-gcp-project-id.iam.gserviceaccount.com',
      perimeter: 'sp_eagleeye_retail_prod',
      diagnosis: 'Gemini Enterprise federated connector identity missing from Access Level al_gemini_enterprise_trusted.',
      gcloudCli:
        'gcloud access-context-manager levels update al_gemini_enterprise_trusted --policy=policy_retail_global_01 --basic-level-spec=gemini_connector_members.yaml',
      terraformHcl: `resource "google_access_context_manager_access_level" "gemini_enterprise_trusted" {
  parent = "accessPolicies/policy_retail_global_01"
  name   = "accessPolicies/policy_retail_global_01/accessLevels/al_gemini_enterprise_trusted"
  title  = "Gemini Enterprise Federated Connectors"
  basic {
    conditions {
      members = ["serviceAccount:sa-gemini-enterprise-connector@your-gcp-project-id.iam.gserviceaccount.com"]
    }
  }
}`,
    },
  ],
  connectors: [
    {
      connectorId: 'conn-atlassian-rovo-prod',
      displayName: 'Atlassian Rovo (Jira & Confluence SRE Runbooks)',
      provider: 'Atlassian Cloud',
      oauthStatus: 'VALID_TOKEN',
      tokenTtlSeconds: 3420,
      quotaUsedPct: 38.4,
      healthy: true,
    },
    {
      connectorId: 'conn-google-workspace-prod',
      displayName: 'Google Workspace (Docs, Slides & Sheets Postmortem Studio)',
      provider: 'Google Workspace',
      oauthStatus: 'VALID_TOKEN',
      tokenTtlSeconds: 3590,
      quotaUsedPct: 21.5,
      healthy: true,
    },
    {
      connectorId: 'conn-pagerduty-incident-bridge',
      displayName: 'PagerDuty On-Call Escalation Bridge',
      provider: 'PagerDuty',
      oauthStatus: 'REFRESH_REQUIRED_SOON',
      tokenTtlSeconds: 420,
      quotaUsedPct: 74.0,
      healthy: true,
    },
  ],
};

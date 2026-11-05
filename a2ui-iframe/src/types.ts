// Copyright 2026 EagleEye Guardian Contributors
// SPDX-License-Identifier: Apache-2.0

export type WorkbenchTabId = 'capacity' | 'hyperdisk' | 'spanner' | 'security';

export interface RegionCapacityRow {
  region: string;
  legacyN1Vms: number;
  modernGen34Vms: number;
  targetFamilies: string[];
  bfcmHeadroomPct: number;
  idleStandbyVms: number;
  posP99Ms: number;
  exhaustedZone: string | null;
}

export interface GpuAdvisorConfig {
  workloadType: 'checkpointed_training' | 'uninterrupted_dense_sync' | 'long_horizon_run';
  requestedGpus: number;
  durationDays: number;
  preferredRegion: string;
}

export interface HyperdiskDefaults {
  capacityTib: number;
  iops: number;
  throughputMib: number;
  discountPct: number;
  retiredStandbyVms: number;
  tornWriteProtection: boolean;
}

export interface SpannerSplitRow {
  splitId: string;
  keyRange: string;
  qps: number;
  p99ReadMs: number;
  p99WriteMs: number;
  cpuUtilizationPct: number;
  isHotKey: boolean;
  remediationNote: string;
}

export interface VpcScViolation {
  violationId: string;
  reason: 'SECURITY_POLICY_VIOLATED' | 'SERVICE_NOT_ALLOWED_FROM_VPC' | 'NO_MATCHING_ACCESS_LEVEL';
  targetService: string;
  methodName: string;
  principalEmail: string;
  perimeter: string;
  diagnosis: string;
  gcloudCli: string;
  terraformHcl: string;
}

export interface FederatedConnectorCard {
  connectorId: string;
  displayName: string;
  provider: string;
  oauthStatus: string;
  tokenTtlSeconds: number;
  quotaUsedPct: number;
  healthy: boolean;
}

export interface WorkbenchHydratedState {
  activeTab: WorkbenchTabId;
  slaTargetMs: number;
  incident: {
    id: string;
    region: string;
    zone: string;
    p99Ms: number;
    status: string;
  };
  hyperdiskDefaults: HyperdiskDefaults;
  regionsMatrix: RegionCapacityRow[];
  spannerSplits: SpannerSplitRow[];
  vpcViolations: VpcScViolation[];
  connectors: FederatedConnectorCard[];
}

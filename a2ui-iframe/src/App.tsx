// Copyright 2026 EagleEye Guardian Contributors
// SPDX-License-Identifier: Apache-2.0

import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  Cpu,
  Database,
  HardDrive,
  Send,
  ShieldAlert,
  SunMoon,
  Zap,
} from 'lucide-react';
import { dispatchA2UIAction, hydrateStateFromHash } from './codec';
import { DEFAULT_WORKBENCH_STATE } from './demoData';
import { GpuAdvisorConfig, WorkbenchHydratedState, WorkbenchTabId } from './types';

export const App: React.FC = () => {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [hydrated, setHydrated] = useState<WorkbenchHydratedState>(DEFAULT_WORKBENCH_STATE);
  const [hydrationSource, setHydrationSource] = useState<'deflate-raw-hash' | 'standalone-demo'>(
    'standalone-demo',
  );
  const [activeTab, setActiveTab] = useState<WorkbenchTabId>('capacity');
  const [lastDispatchedPrompt, setLastDispatchedPrompt] = useState<string | null>(null);

  // Tab 1: Interactive G4 GPU Placement Advisor state
  const [gpuConfig, setGpuConfig] = useState<GpuAdvisorConfig>({
    workloadType: 'checkpointed_training',
    requestedGpus: 64,
    durationDays: 5,
    preferredRegion: 'europe-west2',
  });

  // Tab 2: Interactive Hyperdisk Balanced HA & Reservation FinOps Calculator state
  const [capacityTib, setCapacityTib] = useState<number>(64);
  const [provisionedIops, setProvisionedIops] = useState<number>(320000);
  const [throughputMib, setThroughputMib] = useState<number>(12000);
  const [discountPct, setDiscountPct] = useState<number>(28);
  const [retiredStandbyVms, setRetiredStandbyVms] = useState<number>(16);
  const [tornWriteProtection, setTornWriteProtection] = useState<boolean>(true);

  // Tab 3: Interactive Cloud Spanner load-test target QPS state
  const [spannerTargetQps, setSpannerTargetQps] = useState<number>(150000);
  const [useInterleavedSchema, setUseInterleavedSchema] = useState<boolean>(true);

  // Tab 4: Selected VPC-SC violation index
  const [selectedViolationIdx, setSelectedViolationIdx] = useState<number>(0);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  useEffect(() => {
    const loadFromHash = async () => {
      const { state, hydrationSource: src } = await hydrateStateFromHash(window.location.hash);
      setHydrated(state);
      setHydrationSource(src);
      setActiveTab(state.activeTab);
      setCapacityTib(state.hyperdiskDefaults.capacityTib);
      setProvisionedIops(state.hyperdiskDefaults.iops);
      setThroughputMib(state.hyperdiskDefaults.throughputMib);
      setDiscountPct(state.hyperdiskDefaults.discountPct);
      setRetiredStandbyVms(state.hyperdiskDefaults.retiredStandbyVms);
      setTornWriteProtection(state.hyperdiskDefaults.tornWriteProtection);
    };
    void loadFromHash();
    window.addEventListener('hashchange', loadFromHash);
    return () => window.removeEventListener('hashchange', loadFromHash);
  }, []);

  const triggerAction = (
    actionName: string,
    prompt: string,
    payload: Record<string, unknown> = {},
  ) => {
    dispatchA2UIAction(actionName, prompt, payload);
    setLastDispatchedPrompt(`[a2ui_action -> ${actionName}] ${prompt}`);
  };

  // GPU Advisor recommendation calculation
  const gpuRecommendation = useMemo(() => {
    const nodes = Math.max(1, Math.ceil(gpuConfig.requestedGpus / 8));
    if (gpuConfig.workloadType === 'checkpointed_training') {
      return {
        model: 'SPOT_VM',
        headline: 'Spot VMs (g4-standard-384 / 8x NVIDIA RTX PRO 6000)',
        discount: '68% Est. Spot Savings',
        zones: `${gpuConfig.preferredRegion}-a, us-east1-b`,
        nodes,
        rationale:
          'Checkpointed training tolerates preemption: place on Spot g4-standard-384 instances with automated checkpoint recovery.',
      };
    }
    if (gpuConfig.durationDays <= 7) {
      return {
        model: 'DWS_FLEX_START',
        headline: 'Dynamic Workload Scheduler (DWS) Flex-start (<= 7 Days)',
        discount: '42% Est. DWS Discount',
        zones: `${gpuConfig.preferredRegion}-c, europe-west1-b`,
        nodes,
        rationale:
          'Uninterrupted run within 7-day window: use DWS Flex-start to co-allocate non-preemptible NVIDIA RTX PRO 6000 blocks.',
      };
    }
    return {
      model: 'CROSS_REGION_SPILLOVER',
      headline: 'Cross-Region Spillover (us-east4 / europe-west1)',
      discount: '25% CUD Spillover Rate',
      zones: 'us-east4-b, europe-west1-d',
      nodes,
      rationale:
        'Duration exceeds 7-day DWS Flex-start limit: spillover to secondary region with available on-demand G4 headroom.',
    };
  }, [gpuConfig]);

  // Hyperdisk Balanced HA FinOps live calculation
  const finopsMetrics = useMemo(() => {
    const discountMult = Math.max(0.1, 1 - discountPct / 100);
    const legacyStorageCost = capacityTib * 1024 * 0.17 * 2 * discountMult;
    const standbyVmCost = retiredStandbyVms * 1150;
    const legacyMonthlyTotal = legacyStorageCost + standbyVmCost;

    const hdCapCost = capacityTib * 1024 * 0.16 * discountMult;
    const hdIopsCost = Math.max(0, provisionedIops - 3000) * 0.012 * discountMult;
    const hdTputCost = Math.max(0, throughputMib - 140) * 0.045 * discountMult;
    const hdMonthlyTotal = hdCapCost + hdIopsCost + hdTputCost;

    const monthlyNetSavings = legacyMonthlyTotal - hdMonthlyTotal;
    const annualNetSavings = monthlyNetSavings * 12;

    return {
      legacyMonthlyTotal: Math.round(legacyMonthlyTotal),
      hdMonthlyTotal: Math.round(hdMonthlyTotal),
      monthlyNetSavings: Math.round(monthlyNetSavings),
      annualNetSavings: Math.round(annualNetSavings),
    };
  }, [capacityTib, provisionedIops, throughputMib, discountPct, retiredStandbyVms]);

  const selectedViolation =
    hydrated.vpcViolations[selectedViolationIdx] ?? hydrated.vpcViolations[0];

  return (
    <div className="workbench-shell">
      <header className="topbar">
        <div>
          <h1 className="brand-title">
            <Activity size={20} /> EagleEye Guardian — SRE Command Center
          </h1>
          <p className="brand-subtitle">
            Global Retail POS &amp; Loyalty Reliability Platform (SLA &lt; {hydrated.slaTargetMs}ms
            p99) | Hydration: <strong>{hydrationSource}</strong>
          </p>
        </div>
        <div className="badge-row">
          <span className="pill alert">
            {hydrated.incident.id}: {hydrated.incident.region} ({hydrated.incident.p99Ms}ms p99)
          </span>
          <span className="pill ok">A2UI v0.9 Bridge Ready</span>
          <button
            type="button"
            className="btn secondary"
            onClick={() => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))}
          >
            <SunMoon size={15} /> {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </button>
        </div>
      </header>

      <nav className="tabs-bar" aria-label="SRE Workbench Tabs">
        <button
          type="button"
          className={`tab-btn ${activeTab === 'capacity' ? 'active' : ''}`}
          onClick={() => setActiveTab('capacity')}
        >
          <Cpu size={16} /> 1. BFCM Capacity &amp; N1 Exit
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'hyperdisk' ? 'active' : ''}`}
          onClick={() => setActiveTab('hyperdisk')}
        >
          <HardDrive size={16} /> 2. Hyperdisk HA &amp; FinOps
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'spanner' ? 'active' : ''}`}
          onClick={() => setActiveTab('spanner')}
        >
          <Database size={16} /> 3. Spanner Load &amp; Splits
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'security' ? 'active' : ''}`}
          onClick={() => setActiveTab('security')}
        >
          <ShieldAlert size={16} /> 4. VPC-SC &amp; Connectors
        </button>
      </nav>

      {activeTab === 'capacity' && (
        <div>
          <section className="card">
            <h3>Global Retail Fleet — Legacy N1 Exit vs. Gen 3/4 (C4/N4/C3/C3D) BFCM Headroom</h3>
            <p className="hint">
              Cross-family spillover prevents ZONE_RESOURCE_POOL_EXHAUSTED during Black Friday /
              Cyber Monday retail traffic spikes.
            </p>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Region</th>
                  <th>POS p99 (ms)</th>
                  <th>Legacy N1 VMs</th>
                  <th>Gen 3/4 (C4/N4/C3) VMs</th>
                  <th>Idle Standby VMs</th>
                  <th>BFCM Headroom</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {hydrated.regionsMatrix.map((row) => (
                  <tr key={row.region}>
                    <td>
                      <strong>{row.region}</strong>
                      {row.exhaustedZone ? ` (${row.exhaustedZone})` : ''}
                    </td>
                    <td>{row.posP99Ms} ms</td>
                    <td>{row.legacyN1Vms}</td>
                    <td>{row.modernGen34Vms}</td>
                    <td>{row.idleStandbyVms}</td>
                    <td>{row.bfcmHeadroomPct}%</td>
                    <td>
                      <button
                        type="button"
                        className="btn secondary"
                        onClick={() =>
                          triggerAction(
                            'drain_exhausted_zone',
                            `Migrate ${row.legacyN1Vms} legacy N1 VMs in ${row.region} to ${row.targetFamilies.join('/')} with multi-zone spillover.`,
                            {
                              region: row.region,
                              zone: row.exhaustedZone ?? `${row.region}-a`,
                              incidentId: hydrated.incident.id,
                            },
                          )
                        }
                      >
                        <Zap size={13} /> Spillover to C4/N4
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section className="card">
            <h3>Interactive AI/ML G4 GPU Placement Advisor (NVIDIA RTX PRO 6000)</h3>
            <p className="hint">
              Compare Spot VMs (g4-standard-384), Dynamic Workload Scheduler (DWS) Flex-start (up
              to 7 days), and cross-region spillover.
            </p>
            <div className="grid-2">
              <div>
                <div className="slider-group">
                  <label htmlFor="gpu-workload">
                    <span>Workload Fault-Tolerance Profile</span>
                  </label>
                  <select
                    id="gpu-workload"
                    value={gpuConfig.workloadType}
                    onChange={(e) =>
                      setGpuConfig({
                        ...gpuConfig,
                        workloadType: e.target.value as GpuAdvisorConfig['workloadType'],
                      })
                    }
                    style={{ width: '100%', padding: '8px', borderRadius: '6px' }}
                  >
                    <option value="checkpointed_training">
                      Checkpointed Training / Batch Inference (Fault-Tolerant)
                    </option>
                    <option value="uninterrupted_dense_sync">
                      Uninterrupted Multi-Node Run (&lt;= 7 Days)
                    </option>
                    <option value="long_horizon_run">
                      Long-Horizon Continuous Training (&gt; 7 Days)
                    </option>
                  </select>
                </div>

                <div className="slider-group">
                  <label htmlFor="gpu-count">
                    <span>Requested NVIDIA RTX PRO 6000 GPUs</span>
                    <span>
                      {gpuConfig.requestedGpus} GPUs ({gpuRecommendation.nodes}x g4-standard-384)
                    </span>
                  </label>
                  <input
                    id="gpu-count"
                    type="range"
                    min={8}
                    max={256}
                    step={8}
                    value={gpuConfig.requestedGpus}
                    onChange={(e) =>
                      setGpuConfig({ ...gpuConfig, requestedGpus: Number(e.target.value) })
                    }
                  />
                </div>

                <div className="slider-group">
                  <label htmlFor="gpu-days">
                    <span>Continuous Run Duration (Days)</span>
                    <span>{gpuConfig.durationDays} days</span>
                  </label>
                  <input
                    id="gpu-days"
                    type="range"
                    min={1}
                    max={14}
                    step={1}
                    value={gpuConfig.durationDays}
                    onChange={(e) =>
                      setGpuConfig({ ...gpuConfig, durationDays: Number(e.target.value) })
                    }
                  />
                </div>
              </div>

              <div>
                <div className="kpi-grid">
                  <div className="kpi-box">
                    <div className="label">Recommended Consumption Model</div>
                    <div className="value">{gpuRecommendation.model}</div>
                  </div>
                  <div className="kpi-box">
                    <div className="label">Estimated Cost Advantage</div>
                    <div className="value">{gpuRecommendation.discount}</div>
                  </div>
                </div>
                <p className="hint">
                  <strong>{gpuRecommendation.headline}</strong> — Candidate Zones:{' '}
                  <code>{gpuRecommendation.zones}</code>. {gpuRecommendation.rationale}
                </p>
                <button
                  type="button"
                  className="btn"
                  onClick={() =>
                    triggerAction(
                      'reserve_g4_gpu_placement',
                      `Stage ${gpuRecommendation.model} placement for ${gpuConfig.requestedGpus}x NVIDIA RTX PRO 6000 GPUs (${gpuRecommendation.nodes}x g4-standard-384) in ${gpuRecommendation.zones} for ${gpuConfig.durationDays} days.`,
                      {
                        recommendedModel: gpuRecommendation.model,
                        machineType: 'g4-standard-384',
                        requestedGpus: gpuConfig.requestedGpus,
                        durationDays: gpuConfig.durationDays,
                      },
                    )
                  }
                >
                  <Send size={14} /> Dispatch G4 Placement Plan to Agent
                </button>
              </div>
            </div>
          </section>
        </div>
      )}

      {activeTab === 'hyperdisk' && (
        <section className="card">
          <h3>Regional Hyperdisk Balanced HA &amp; Idle Standby Reservation FinOps Calculator</h3>
          <p className="hint">
            Model 50+ TB MySQL modernization from Zonal SSD PD (100k IOPS, 1,200 MiB/s cap) to
            Regional Hyperdisk Balanced HA (up to 640k IOPS, 20,000 MiB/s, RPO=0, &lt;2.5m RTO,
            Torn-Write Protection, 1x/4h dynamic scaling).
          </p>
          <div className="grid-2">
            <div>
              <div className="slider-group">
                <label htmlFor="hd-cap">
                  <span>Cluster Storage Capacity (TiB)</span>
                  <span>{capacityTib} TiB</span>
                </label>
                <input
                  id="hd-cap"
                  type="range"
                  min={50}
                  max={256}
                  step={2}
                  value={capacityTib}
                  onChange={(e) => setCapacityTib(Number(e.target.value))}
                />
              </div>

              <div className="slider-group">
                <label htmlFor="hd-iops">
                  <span>Provisioned Hyperdisk Balanced HA IOPS (Max 640,000)</span>
                  <span>{provisionedIops.toLocaleString()} IOPS</span>
                </label>
                <input
                  id="hd-iops"
                  type="range"
                  min={50000}
                  max={640000}
                  step={10000}
                  value={provisionedIops}
                  onChange={(e) => setProvisionedIops(Number(e.target.value))}
                />
              </div>

              <div className="slider-group">
                <label htmlFor="hd-tput">
                  <span>Provisioned Throughput (Max 20,000 MiB/s)</span>
                  <span>{throughputMib.toLocaleString()} MiB/s</span>
                </label>
                <input
                  id="hd-tput"
                  type="range"
                  min={1200}
                  max={20000}
                  step={400}
                  value={throughputMib}
                  onChange={(e) => setThroughputMib(Number(e.target.value))}
                />
              </div>

              <div className="slider-group">
                <label htmlFor="hd-discount">
                  <span>Contractual Enterprise Discount (%)</span>
                  <span>{discountPct}%</span>
                </label>
                <input
                  id="hd-discount"
                  type="range"
                  min={0}
                  max={55}
                  step={1}
                  value={discountPct}
                  onChange={(e) => setDiscountPct(Number(e.target.value))}
                />
              </div>

              <div className="slider-group">
                <label htmlFor="hd-standby">
                  <span>Retired Idle Standby VMs (Replaced by RPO=0 Regional HA)</span>
                  <span>{retiredStandbyVms} VMs</span>
                </label>
                <input
                  id="hd-standby"
                  type="range"
                  min={0}
                  max={48}
                  step={2}
                  value={retiredStandbyVms}
                  onChange={(e) => setRetiredStandbyVms(Number(e.target.value))}
                />
              </div>

              <div className="slider-group">
                <label>
                  <span>
                    <input
                      type="checkbox"
                      checked={tornWriteProtection}
                      onChange={(e) => setTornWriteProtection(e.target.checked)}
                    />{' '}
                    Enable 16KB Atomic Torn-Write Protection (Disable MySQL Doublewrite Buffer)
                  </span>
                </label>
              </div>
            </div>

            <div>
              <div className="kpi-grid">
                <div className="kpi-box">
                  <div className="label">Legacy Zonal SSD PD + Standby Cost</div>
                  <div className="value">${finopsMetrics.legacyMonthlyTotal.toLocaleString()}/mo</div>
                </div>
                <div className="kpi-box">
                  <div className="label">Regional Hyperdisk Balanced HA Cost</div>
                  <div className="value">${finopsMetrics.hdMonthlyTotal.toLocaleString()}/mo</div>
                </div>
                <div className="kpi-box">
                  <div className="label">Projected Monthly Net Savings</div>
                  <div className="value">${finopsMetrics.monthlyNetSavings.toLocaleString()}/mo</div>
                </div>
                <div className="kpi-box">
                  <div className="label">Projected Annual Net Savings</div>
                  <div className="value">${finopsMetrics.annualNetSavings.toLocaleString()}/yr</div>
                </div>
              </div>
              <p className="hint">
                <strong>RPO=0 &amp; &lt;2.5m RTO:</strong> Synchronous dual-zone replication with{' '}
                {tornWriteProtection
                  ? 'innodb_doublewrite=OFF (30% write throughput boost)'
                  : 'standard doublewrite buffer'}{' '}
                and 3-day Snapshot Recycle Bin guardrail.
              </p>
              <button
                type="button"
                className="btn"
                onClick={() =>
                  triggerAction(
                    'scale_hyperdisk_iops',
                    `Scale Regional Hyperdisk Balanced HA (${capacityTib} TiB) to ${provisionedIops} IOPS and ${throughputMib} MiB/s with tornWriteProtection=${tornWriteProtection}, retiring ${retiredStandbyVms} standby VMs.`,
                    {
                      region: hydrated.incident.region,
                      capacityTib,
                      targetIops: provisionedIops,
                      targetThroughputMib: throughputMib,
                      retiredStandbyVms,
                      tornWriteProtection,
                    },
                  )
                }
              >
                <Send size={14} /> Stage Hyperdisk Balanced HA Scaling Gate
              </button>
            </div>
          </div>
        </section>
      )}

      {activeTab === 'spanner' && (
        <section className="card">
          <h3>Cloud Spanner Transactional Loyalty Ledger Load-Test &amp; Split Visualizer</h3>
          <p className="hint">
            Inspect QPS vs. p99 read/write latency, split-boundary health, hot-key detection, and
            parent-child schema interleaving across LoyaltyWallets -&gt; CouponRedemptions.
          </p>
          <div className="grid-2">
            <div>
              <div className="slider-group">
                <label htmlFor="spanner-qps">
                  <span>Target Transactional Load-Test QPS</span>
                  <span>{spannerTargetQps.toLocaleString()} QPS</span>
                </label>
                <input
                  id="spanner-qps"
                  type="range"
                  min={50000}
                  max={300000}
                  step={10000}
                  value={spannerTargetQps}
                  onChange={(e) => setSpannerTargetQps(Number(e.target.value))}
                />
              </div>
              <div className="slider-group">
                <label>
                  <span>
                    <input
                      type="checkbox"
                      checked={useInterleavedSchema}
                      onChange={(e) => setUseInterleavedSchema(e.target.checked)}
                    />{' '}
                    Enforce INTERLEAVE IN PARENT LoyaltyWallets + Bit-Reversed Shard Hash
                  </span>
                </label>
              </div>
              <button
                type="button"
                className="btn"
                onClick={() =>
                  triggerAction(
                    'trigger_spanner_load_test',
                    `Run Cloud Spanner transactional ledger load test at ${spannerTargetQps} QPS with useInterleavedSchema=${useInterleavedSchema}.`,
                    {
                      targetQps: spannerTargetQps,
                      useInterleavedSchema,
                    },
                  )
                }
              >
                <Send size={14} /> Run Long-Running Spanner Load Test
              </button>
            </div>

            <div className="kpi-grid">
              <div className="kpi-box">
                <div className="label">Simulated p99 Read Latency</div>
                <div className="value">{useInterleavedSchema ? '6.8 ms' : '19.4 ms'}</div>
              </div>
              <div className="kpi-box">
                <div className="label">Simulated p99 Write Latency</div>
                <div className="value">{useInterleavedSchema ? '14.2 ms' : '38.7 ms'}</div>
              </div>
              <div className="kpi-box">
                <div className="label">250ms POS SLA Headroom</div>
                <div className="value">{useInterleavedSchema ? '94.3%' : '84.5%'}</div>
              </div>
            </div>
          </div>

          <table className="data-table" style={{ marginTop: '14px' }}>
            <thead>
              <tr>
                <th>Split ID</th>
                <th>Key Range / Table Hierarchy</th>
                <th>QPS</th>
                <th>p99 Read</th>
                <th>p99 Write</th>
                <th>CPU %</th>
                <th>Split Health &amp; Advice</th>
              </tr>
            </thead>
            <tbody>
              {hydrated.spannerSplits.map((sp) => (
                <tr key={sp.splitId}>
                  <td>
                    <strong>{sp.splitId}</strong>
                  </td>
                  <td>{sp.keyRange}</td>
                  <td>{sp.qps.toLocaleString()}</td>
                  <td>{sp.p99ReadMs} ms</td>
                  <td>{sp.p99WriteMs} ms</td>
                  <td>{sp.cpuUtilizationPct}%</td>
                  <td>
                    {sp.isHotKey ? 'HOT-KEY DETECTED: ' : 'BALANCED: '}
                    {sp.remediationNote}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {activeTab === 'security' && (
        <div>
          <section className="card">
            <h3>VPC Service Controls (VPC-SC) Audit Violation Inspector &amp; Policy Generator</h3>
            <p className="hint">
              Select a VpcServiceControlAuditMetadata violation to inspect ready-to-apply gcloud
              and Terraform ingress/egress policies.
            </p>
            <div className="badge-row" style={{ marginBottom: '12px' }}>
              {hydrated.vpcViolations.map((v, idx) => (
                <button
                  key={v.violationId}
                  type="button"
                  className={`btn ${selectedViolationIdx === idx ? '' : 'secondary'}`}
                  onClick={() => setSelectedViolationIdx(idx)}
                >
                  {v.violationId}: {v.reason} ({v.targetService})
                </button>
              ))}
            </div>

            {selectedViolation && (
              <div className="grid-2">
                <div>
                  <p className="hint">
                    <strong>Principal:</strong> <code>{selectedViolation.principalEmail}</code>
                    <br />
                    <strong>Method:</strong> <code>{selectedViolation.methodName}</code>
                    <br />
                    <strong>Perimeter:</strong> <code>{selectedViolation.perimeter}</code>
                    <br />
                    <strong>Diagnosis:</strong> {selectedViolation.diagnosis}
                  </p>
                  <div className="code-block">{selectedViolation.gcloudCli}</div>
                  <div style={{ marginTop: '10px' }}>
                    <button
                      type="button"
                      className="btn"
                      onClick={() =>
                        triggerAction(
                          'apply_vpc_sc_remediation',
                          `Stage VPC-SC perimeter policy remediation for ${selectedViolation.violationId} (${selectedViolation.reason} on ${selectedViolation.targetService}).`,
                          {
                            violationId: selectedViolation.violationId,
                            reason: selectedViolation.reason,
                            targetService: selectedViolation.targetService,
                            perimeter: selectedViolation.perimeter,
                          },
                        )
                      }
                    >
                      <Send size={14} /> Stage VPC-SC Policy Remediation in Chat
                    </button>
                  </div>
                </div>
                <div>
                  <div className="code-block">{selectedViolation.terraformHcl}</div>
                </div>
              </div>
            )}
          </section>

          <section className="card">
            <h3>Gemini Enterprise Federated Connectors &amp; OAuth Guard</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Connector</th>
                  <th>Provider</th>
                  <th>OAuth Status</th>
                  <th>Token TTL</th>
                  <th>Quota Used</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {hydrated.connectors.map((c) => (
                  <tr key={c.connectorId}>
                    <td>
                      <strong>{c.displayName}</strong>
                    </td>
                    <td>{c.provider}</td>
                    <td>{c.oauthStatus}</td>
                    <td>{c.tokenTtlSeconds}s</td>
                    <td>{c.quotaUsedPct}%</td>
                    <td>
                      <button
                        type="button"
                        className="btn secondary"
                        onClick={() =>
                          triggerAction(
                            'verify_connector_oauth',
                            `Verify OAuth token health and quota utilization for ${c.displayName} (${c.connectorId}).`,
                            { connectorId: c.connectorId },
                          )
                        }
                      >
                        Verify OAuth
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      )}

      {lastDispatchedPrompt && (
        <div className="toast-banner" role="status">
          <strong>Dispatched via postMessage Bridge:</strong> {lastDispatchedPrompt}
        </div>
      )}
    </div>
  );
};

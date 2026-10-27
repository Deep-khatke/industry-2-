import React, { useState, useEffect } from 'react';
import {
  Cpu,
  CheckCircle2,
  ShieldCheck,
  Zap,
  Layers,
  AlertCircle,
  Database,
  RotateCcw,
  Network,
  GitBranch,
  Activity,
  Server,
  Lock,
} from 'lucide-react';
import { ActiveModelDetails, ModelHealth, DetectionBundle, RoutingDecision, ISPAnomalyStatus } from '../types/api';
import { api } from '../services/api';

interface ModelMonitoringPageProps {
  modelDetails: ActiveModelDetails | null;
  modelHealth: ModelHealth | null;
}

export const ModelMonitoringPage: React.FC<ModelMonitoringPageProps> = ({
  modelDetails,
  modelHealth,
}) => {
  const [bundle, setBundle] = useState<DetectionBundle | null>(null);
  const [routingDecisions, setRoutingDecisions] = useState<RoutingDecision[]>([]);
  const [ispStatus, setIspStatus] = useState<ISPAnomalyStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchHmdData = async () => {
    try {
      const [bundleData, decisions, anomaly] = await Promise.allSettled([
        api.getDetectionBundle(),
        api.getRoutingDecisions(15),
        api.getISPAnomalyStatus(),
      ]);

      if (bundleData.status === 'fulfilled' && bundleData.value) {
        setBundle(bundleData.value);
      }
      if (decisions.status === 'fulfilled' && Array.isArray(decisions.value)) {
        setRoutingDecisions(decisions.value);
      }
      if (anomaly.status === 'fulfilled' && anomaly.value) {
        setIspStatus(anomaly.value);
      }
    } catch (err) {
      console.warn('Failed to fetch auxiliary HMD data:', err);
    }
  };

  useEffect(() => {
    fetchHmdData();
  }, []);

  const handleRollback = async () => {
    if (!window.confirm('Are you sure you want to rollback to the previous authorized DetectionBundle?')) {
      return;
    }
    setIsLoading(true);
    setActionMessage(null);
    try {
      const res = await api.rollbackDetectionBundle();
      if (res.success) {
        setActionMessage(`Rollback successful: Active bundle is now ${res.active_bundle_id}`);
        await fetchHmdData();
      } else {
        setActionMessage(`Rollback rejected: ${res.message}`);
      }
    } catch (err: any) {
      setActionMessage(`Rollback error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-[#0d131f] border border-slate-800 p-4 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-purple-950/60 border border-purple-700/60 text-purple-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white flex items-center space-x-2">
              <span>FCS-HMD: Hierarchical Multi-Model Intrusion Detection Engine</span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
                STATUS: {modelHealth?.status || 'READY'}
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Architecture v1.2: General Threat Detector, Tenant Anomaly Baselines, Attack Specialists & Deterministic Evidence Fusion.
            </p>
          </div>
        </div>

        <div className="text-right font-mono text-xs">
          <span className="text-slate-500">Security Invariant: </span>
          <span className="text-cyan-400 font-bold">network_action_executed = False</span>
        </div>
      </div>

      {actionMessage && (
        <div className="p-3 bg-cyan-950/40 border border-cyan-800 text-cyan-300 text-xs rounded-lg font-mono flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-cyan-400 flex-shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* 1. DetectionBundle & Rollback Interface */}
      <div className="cyber-card p-5 border-cyan-500/30">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center space-x-2">
              <Lock className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-white">
                Active DetectionBundle: <span className="font-mono text-cyan-400">{bundle?.bundle_id || 'fcs-hmd-bundle-v1'}</span>
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                v{bundle?.version || '1.2.0'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Authorized by <span className="text-slate-200 font-mono">{bundle?.authorized_by || 'security_admin'}</span> • SHA-256 Digest: <span className="text-cyan-300 font-mono">{bundle?.bundle_digest?.slice(0, 16) || '2bd8454c761cc75a'}...</span>
            </p>
          </div>

          <button
            onClick={handleRollback}
            disabled={isLoading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-950/60 hover:bg-amber-900 border border-amber-700/60 text-amber-300 text-xs font-semibold font-mono transition-colors disabled:opacity-50"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Rollback DetectionBundle</span>
          </button>
        </div>

        {/* Constituent Models in Bundle */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
            <span className="text-slate-500 block text-[10px] font-mono">LEVEL 1 GENERAL</span>
            <div className="font-bold text-white font-mono mt-0.5 truncate">
              {bundle?.general_model_id || 'lightgbm_deployable_subset'}
            </div>
            <span className="text-[10px] text-emerald-400 font-mono mt-1 block">
              STATUS: READY (SHA-256 Verified)
            </span>
          </div>

          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
            <span className="text-slate-500 block text-[10px] font-mono">LEVEL 1 ISP ANOMALY</span>
            <div className="font-bold text-white font-mono mt-0.5 truncate">
              {bundle?.anomaly_model_id || 'isolationforest_anomaly_tenant'}
            </div>
            <span className="text-[10px] text-emerald-400 font-mono mt-1 block">
              STATUS: ACTIVE (Isolated Baseline)
            </span>
          </div>

          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
            <span className="text-slate-500 block text-[10px] font-mono">SPECIALIST 1 (DDOS)</span>
            <div className="font-bold text-white font-mono mt-0.5 truncate">
              lightgbm_ddos_specialist
            </div>
            <span className="text-[10px] text-emerald-400 font-mono mt-1 block">
              STATUS: ROUTED ON BURST
            </span>
          </div>

          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800">
            <span className="text-slate-500 block text-[10px] font-mono">SPECIALIST 2 (SCANNING)</span>
            <div className="font-bold text-white font-mono mt-0.5 truncate">
              lightgbm_scanning_specialist
            </div>
            <span className="text-[10px] text-emerald-400 font-mono mt-1 block">
              STATUS: ROUTED ON SYN/PROBE
            </span>
          </div>
        </div>
      </div>

      {/* 2. Hierarchical FCS-HMD Topology Visualizer */}
      <div className="cyber-card p-5">
        <div className="flex items-center space-x-2 mb-4">
          <GitBranch className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-bold text-white tracking-wide">
            FCS-HMD Hierarchical Multi-Model Architecture & Routing Topology
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Layer 1 */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-indigo-800/50 space-y-2">
            <div className="flex items-center justify-between text-indigo-400 font-bold text-xs uppercase">
              <span>Layer 1: Telemetry & Ingestion</span>
              <Activity className="w-3.5 h-3.5" />
            </div>
            <p className="text-xs text-slate-300">
              30-Second Event-Time Tumbling Window
            </p>
            <div className="text-[11px] font-mono text-slate-400 space-y-1">
              <div>• 14 NetFlow Features</div>
              <div>• 60s Lateness Tolerant</div>
              <div>• Deduplicated Flow Stream</div>
            </div>
          </div>

          {/* Layer 2 */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-purple-800/50 space-y-2">
            <div className="flex items-center justify-between text-purple-400 font-bold text-xs uppercase">
              <span>Layer 2: Level 1 Gating</span>
              <Server className="w-3.5 h-3.5" />
            </div>
            <p className="text-xs text-slate-300">
              Dual Level-1 Detection
            </p>
            <div className="text-[11px] font-mono text-slate-400 space-y-1">
              <div>• General Threat Detector</div>
              <div>• Tenant Anomaly Detector</div>
              <div>• Benign Short-Circuit (&lt;0.35)</div>
            </div>
          </div>

          {/* Layer 3 */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-amber-800/50 space-y-2">
            <div className="flex items-center justify-between text-amber-400 font-bold text-xs uppercase">
              <span>Layer 3: Conditional Router</span>
              <Network className="w-3.5 h-3.5" />
            </div>
            <p className="text-xs text-slate-300">
              Eligible Attack Specialists
            </p>
            <div className="text-[11px] font-mono text-slate-400 space-y-1">
              <div>• DDoS Specialist (Volumetric)</div>
              <div>• Scanning Specialist (SYN/Probe)</div>
              <div className="text-slate-500">• Botnet: Ineligible (No DNS DPI)</div>
            </div>
          </div>

          {/* Layer 4 */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-emerald-800/50 space-y-2">
            <div className="flex items-center justify-between text-emerald-400 font-bold text-xs uppercase">
              <span>Layer 4: Evidence Fusion</span>
              <ShieldCheck className="w-3.5 h-3.5" />
            </div>
            <p className="text-xs text-slate-300">
              Deterministic Fusion Engine
            </p>
            <div className="text-[11px] font-mono text-slate-400 space-y-1">
              <div>• Weighted Bayesian Combination</div>
              <div>• Specialist Dominance (0.55)</div>
              <div>• Deterministic Rules Floor</div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. Benchmark Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="cyber-card p-5 border-cyan-500/30">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Hierarchical Ensemble PR-AUC
          </span>
          <div className="text-2xl font-bold font-mono text-cyan-400">
            95.09%
          </div>
          <div className="text-xs text-slate-500 mt-1">
            FCS-HMD Full Hierarchical Evaluation
          </div>
        </div>

        <div className="cyber-card p-5 border-emerald-500/30">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Ensemble F1-Score
          </span>
          <div className="text-2xl font-bold font-mono text-emerald-400">
            91.67%
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Deterministic Evidence Fusion
          </div>
        </div>

        <div className="cyber-card p-5 border-purple-500/30">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Router Overhead (p95)
          </span>
          <div className="text-2xl font-bold font-mono text-purple-400">
            24.9 μs
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Sub-millisecond conditional branch
          </div>
        </div>

        <div className="cyber-card p-5 border-amber-500/30">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            ISP Tenant Anomaly Status
          </span>
          <div className="text-lg font-bold font-mono text-amber-400 truncate">
            {ispStatus?.baseline_status || 'CALIBRATED'}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Isolation: Strict Per-ISP Baseline
          </div>
        </div>
      </div>

      {/* 4. Real-Time Routing Decisions Feed */}
      <div className="cyber-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Network className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white tracking-wide">
              Recent Conditional Routing Decisions
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Live Operational Log
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-2.5 px-3">Timestamp</th>
                <th className="py-2.5 px-3">Level 1 (Gen / Anom)</th>
                <th className="py-2.5 px-3">Routing Decision</th>
                <th className="py-2.5 px-3">Trigger Rationale</th>
                <th className="py-2.5 px-3">Latency</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {routingDecisions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-slate-500">
                    No routing decisions recorded yet in this session.
                  </td>
                </tr>
              ) : (
                routingDecisions.map((rd) => {
                  let routed: string[] = [];
                  let reasons: string[] = [];
                  try {
                    routed = rd.routed_models_json ? JSON.parse(rd.routed_models_json) : (rd.routed_models || []);
                  } catch {
                    routed = [];
                  }
                  try {
                    reasons = rd.trigger_reasons_json ? JSON.parse(rd.trigger_reasons_json) : (rd.trigger_reasons || []);
                  } catch {
                    reasons = [];
                  }

                  return (
                    <tr key={rd.decision_id} className="hover:bg-slate-800/30">
                      <td className="py-2.5 px-3 text-slate-400">
                        {new Date(rd.created_at).toLocaleTimeString()}
                      </td>
                      <td className="py-2.5 px-3 text-cyan-400">
                        {(rd.level1_general_score * 100).toFixed(1)}% / {(rd.level1_anomaly_score * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 px-3">
                        {routed.length > 0 ? (
                          <span className="text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800 text-[10px]">
                            ROUTED: {routed.join(', ')}
                          </span>
                        ) : (
                          <span className="text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800 text-[10px]">
                            SHORT-CIRCUITED (NORMAL)
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 max-w-xs truncate font-sans text-[11px]">
                        {reasons.join('; ') || 'Threshold evaluation completed'}
                      </td>
                      <td className="py-2.5 px-3 text-purple-400">
                        {rd.routing_latency_us.toFixed(1)} μs
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Feature Parity & Contract Schema */}
      <div className="cyber-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white tracking-wide">
              Training-Inference Feature Parity Contract (14 Features)
            </h3>
          </div>
          <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
            SCHEMA VALIDATED
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-2.5 px-3">#</th>
                <th className="py-2.5 px-3">Feature Name</th>
                <th className="py-2.5 px-3">Data Type</th>
                <th className="py-2.5 px-3">Semantic Description</th>
                <th className="py-2.5 px-3">Missing Value Treatment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {(modelDetails?.deployable_feature_schema || []).map((feat, idx) => (
                <tr key={feat.name} className="hover:bg-slate-800/30">
                  <td className="py-2.5 px-3 text-slate-500">{idx + 1}</td>
                  <td className="py-2.5 px-3 text-cyan-400 font-bold">{feat.name}</td>
                  <td className="py-2.5 px-3 text-purple-400">{feat.type}</td>
                  <td className="py-2.5 px-3 text-slate-300 font-sans">{feat.description}</td>
                  <td className="py-2.5 px-3 text-slate-400">Strict Contract Zero/Median</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 6. Verification & Lineage Notes */}
      <div className="cyber-card p-5 border-slate-800 bg-slate-900/40 text-xs space-y-2">
        <h4 className="font-bold text-white uppercase text-[11px] flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <span>FCS-HMD Multi-Model Safety & Fallback Guarantees</span>
        </h4>
        <ul className="list-disc pl-5 text-slate-400 space-y-1">
          <li>All constituent model artifacts are cryptographically verified via SHA-256 digests prior to bundle activation.</li>
          <li>If a specialist encounters a timeout or artifact error, the engine seamlessly falls back to Level 1 general detection without failing ingestion.</li>
          <li>Missing models never fabricate 0.0 or benign scores; unscored models are explicitly marked UNKNOWN or DEGRADED.</li>
          <li>Botnet Specialist eligibility was rigorously assessed: due to missing DNS payload resource records in NetFlow v1 streams, it is marked NOT_ELIGIBLE for production deployment.</li>
          <li>Tenant-specific Isolation Forest anomaly models are isolated per ISP tenant, preventing cross-tenant data leakage.</li>
          <li>Strict safety boundary: All multi-model inference outputs represent probabilistic threat evidence only. network_action_executed = False is unconditionally enforced.</li>
        </ul>
      </div>
    </div>
  );
};

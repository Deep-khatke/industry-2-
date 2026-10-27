import React, { useEffect, useState } from 'react';
import {
  Share2,
  Shield,
  Lock,
  Cpu,
  Activity,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  Users,
  Database,
  Sliders,
  FileText,
  Play,
  ArrowRight,
} from 'lucide-react';

interface FederationStatus {
  status: string;
  system_name: string;
  version: string;
  framework: string;
  differential_privacy: string;
  secure_aggregation: string;
  active_general_model: string;
  bundle_status: string;
  total_isp_participants: number;
  min_reconstruction_threshold: number;
  registered_candidates_count: number;
  latest_candidate: string | null;
  zero_cost_policy: string;
}

interface Participant {
  participant_id: string;
  name: string;
  role: string;
  connection_status: string;
  data_partition: string;
  partition_size_bytes: number;
  cumulative_epsilon: number;
  remaining_epsilon: number;
  max_epsilon: number;
  target_delta: number;
  is_budget_exhausted: boolean;
  eligibility_status: string;
}

interface CandidateModel {
  candidate_id?: string;
  model_id?: string;
  model_type?: string;
  framework?: string;
  status: string;
  model_digest?: string;
  hash?: string;
  aggregation_protocol?: string;
  test_metrics?: Record<string, number>;
}

export const FederationPage: React.FC = () => {
  const [status, setStatus] = useState<FederationStatus | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [candidates, setCandidates] = useState<CandidateModel[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'participants' | 'privacy' | 'secagg' | 'comparison' | 'governance'>('overview');
  const [loading, setLoading] = useState<boolean>(true);
  const [runningSimulation, setRunningSimulation] = useState<boolean>(false);
  const [simMessage, setSimMessage] = useState<string | null>(null);
  const [dropoutResult, setDropoutResult] = useState<any>(null);

  const fetchFederationData = async () => {
    setLoading(true);
    try {
      const [statusRes, partRes, candRes] = await Promise.all([
        fetch('/v1/federation/status').then((r) => r.json()).catch(() => null),
        fetch('/v1/federation/participants').then((r) => r.json()).catch(() => null),
        fetch('/v1/federation/models').then((r) => r.json()).catch(() => null),
      ]);

      if (statusRes) setStatus(statusRes);
      if (partRes?.participants) setParticipants(partRes.participants);
      if (candRes?.models) setCandidates(candRes.models);
    } catch (e) {
      console.error('Failed to load federation data', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFederationData();
  }, []);

  const triggerSimulation = async (profile: 'research' | 'protected') => {
    setRunningSimulation(true);
    setSimMessage(`Executing 1-round simulation (${profile} profile)...`);
    try {
      const res = await fetch('/v1/dev/federation/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile, partition: 'iid', rounds: 1 }),
      });
      const data = await res.json();
      if (data.status === 'COMPLETED') {
        setSimMessage(`Success! Round completed. Test F1: ${(data.eval_metrics?.f1 || 0).toFixed(4)}, Candidate: ${data.candidate_id || 'Registered'}`);
      } else {
        setSimMessage(`Simulation outcome: ${data.status} - ${data.aborted_reason || 'Unknown'}`);
      }
      fetchFederationData();
    } catch (e: any) {
      setSimMessage(`Error triggering simulation: ${e.message}`);
    } finally {
      setRunningSimulation(false);
    }
  };

  const testDropoutThreshold = async (dropCount: number) => {
    const dropped = dropCount === 1 ? ['isp_02'] : dropCount === 2 ? ['isp_02', 'isp_04'] : ['isp_01', 'isp_02', 'isp_03'];
    try {
      const res = await fetch('/v1/dev/federation/simulate-dropout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dropped_clients: dropped }),
      });
      const data = await res.json();
      setDropoutResult(data);
    } catch (e: any) {
      setDropoutResult({ error: e.message });
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Share2 className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-wide">
                Federated Learning Operations (FCS-PFL)
              </h1>
              <p className="text-sm text-slate-400">
                Privacy-Preserving Threat Intelligence & Multi-ISP Collaborative Defense Architecture v1.2
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => triggerSimulation('protected')}
            disabled={runningSimulation}
            className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-sm flex items-center space-x-2 transition disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            <span>{runningSimulation ? 'Running...' : 'Run Protected FL Round'}</span>
          </button>
          <button
            onClick={fetchFederationData}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {simMessage && (
        <div className="p-4 rounded-xl bg-cyan-950/40 border border-cyan-800/60 text-cyan-200 text-sm flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span>{simMessage}</span>
          </div>
          <button onClick={() => setSimMessage(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Primary KPI Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur">
          <div className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Federation Status</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-white">{status?.status || 'OPERATIONAL'}</div>
          <div className="text-xs text-slate-400 mt-2 font-mono">
            Flower 1.42.0 • SecAgg+ • Opacus
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur">
          <div className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>ISP Participant Cohort</span>
            <Users className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-white">7 Simulated ISPs</div>
          <div className="text-xs text-slate-400 mt-2 font-mono">
            Threshold: k=5 of 7 required
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur">
          <div className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Active General Detector</span>
            <Cpu className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-sm font-bold text-white truncate" title={status?.active_general_model}>
            {status?.active_general_model || 'lightgbm_deployable_subset'}
          </div>
          <div className="text-xs text-emerald-400 mt-2 font-mono">
            Bundle Status: {status?.bundle_status || 'ACTIVE'}
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur">
          <div className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Cost Policy</span>
            <Shield className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-emerald-400">₹0.00 / $0.00</div>
          <div className="text-xs text-slate-400 mt-2 font-mono">
            Zero Paid Cloud Services
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex border-b border-slate-800 space-x-6 text-sm font-medium">
        {[
          { id: 'overview', label: 'Overview & Architecture' },
          { id: 'participants', label: 'Participant Health (7 ISPs)' },
          { id: 'privacy', label: 'Differential Privacy' },
          { id: 'secagg', label: 'Secure Aggregation (SecAgg+)' },
          { id: 'comparison', label: 'Baseline Comparisons' },
          { id: 'governance', label: 'Candidate Registry & Safety' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`pb-3 transition-colors relative ${
              activeTab === tab.id
                ? 'text-cyan-400 font-semibold border-b-2 border-cyan-400'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sub-Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/80 space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <Shield className="w-5 h-5 text-cyan-400" />
              <span>Hierarchical Multi-Model Architecture & Isolation Boundaries</span>
            </h3>
            <p className="text-sm text-slate-300 leading-relaxed">
              FCS-PFL implements collaborative federated learning solely for the <strong>shared general intrusion detection MLP</strong>.
              In strict accordance with FCS Architecture v1.2, <strong>tenant anomaly detectors</strong> (IsolationForest / Autoencoder)
              and specialized threat classifiers (DDoS, Port Scan, Botnet) remain <strong>strictly tenant-local</strong> and are never federated.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60">
                <div className="text-xs font-mono text-cyan-400 uppercase">Shared Federated Model</div>
                <div className="font-semibold text-white mt-1">PyTorch TabularMLPNet</div>
                <div className="text-xs text-slate-400 mt-1">14 deployable NetFlow features, Opacus GroupNorm, binary attack classification.</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60">
                <div className="text-xs font-mono text-purple-400 uppercase">Tenant-Local Anomaly</div>
                <div className="font-semibold text-white mt-1">IsolationForest / Autoencoder</div>
                <div className="text-xs text-slate-400 mt-1">Calibrated on private tenant traffic. Kept outside federation to preserve privacy.</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/60">
                <div className="text-xs font-mono text-emerald-400 uppercase">Tenant Response Invariant</div>
                <div className="font-semibold text-white mt-1">Manual Response Center</div>
                <div className="text-xs text-slate-400 mt-1">AUTO mode permanently disabled. Mitigation requires human operator sign-off.</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sub-Tab 2: Participant Health */}
      {activeTab === 'participants' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-900/40">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-800/60 text-xs font-mono uppercase text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">ISP Participant</th>
                  <th className="py-3 px-4">Partition File</th>
                  <th className="py-3 px-4">Connection</th>
                  <th className="py-3 px-4">Privacy Spent (ε)</th>
                  <th className="py-3 px-4">Remaining (ε)</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {participants.map((p) => (
                  <tr key={p.participant_id} className="hover:bg-slate-800/30">
                    <td className="py-3 px-4 font-medium text-white flex items-center space-x-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-400"></div>
                      <span>{p.participant_id}</span>
                      <span className="text-xs text-slate-500 font-normal">({p.name})</span>
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-slate-400">{p.data_partition}</td>
                    <td className="py-3 px-4 font-mono text-xs text-emerald-400">{p.connection_status}</td>
                    <td className="py-3 px-4 font-mono text-xs">{p.cumulative_epsilon.toFixed(4)}</td>
                    <td className="py-3 px-4 font-mono text-xs text-cyan-400">{p.remaining_epsilon.toFixed(4)}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        {p.eligibility_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sub-Tab 3: Differential Privacy */}
      {activeTab === 'privacy' && (
        <div className="space-y-6">
          <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 space-y-3">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <Lock className="w-4 h-4 text-cyan-400" />
              <span>Opacus DP-SGD Engine & Cumulative Accounting</span>
            </h3>
            <p className="text-sm text-slate-300">
              Each simulated ISP trains locally using Opacus <code>PrivacyEngine</code> with per-example gradient clipping
              and calibrated Gaussian noise addition. Privacy expenditure is tracked by a durable SQLite state machine
              preventing budget exhaustion or double-spending.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-3 font-mono text-xs">
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/60">
                <div className="text-slate-400">Protected Unit</div>
                <div className="text-cyan-400 font-bold mt-1">Single NetFlow Record</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/60">
                <div className="text-slate-400">Target Delta (δ)</div>
                <div className="text-cyan-400 font-bold mt-1">1.0e-05</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/60">
                <div className="text-slate-400">Max Grad Norm (C)</div>
                <div className="text-cyan-400 font-bold mt-1">1.0</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/60">
                <div className="text-slate-400">Noise Multiplier (σ)</div>
                <div className="text-cyan-400 font-bold mt-1">1.1</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sub-Tab 4: Secure Aggregation */}
      {activeTab === 'secagg' && (
        <div className="space-y-6">
          <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 space-y-3">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <Lock className="w-4 h-4 text-purple-400" />
              <span>Flower SecAgg+ Protocol Verification (Threshold k=5 of 7)</span>
            </h3>
            <p className="text-sm text-slate-300">
              SecAgg+ coordinates Diffie-Hellman pairwise key agreement, Shamir secret sharing, and pseudo-random
              masking so the central coordinator receives only the sum of parameter vectors, never individual client weights.
            </p>
            <div className="flex items-center space-x-3 pt-2">
              <button
                onClick={() => testDropoutThreshold(1)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-white border border-slate-700"
              >
                Test 1 Dropout (6 active → Succeed)
              </button>
              <button
                onClick={() => testDropoutThreshold(2)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-white border border-slate-700"
              >
                Test 2 Dropouts (5 active = k → Succeed)
              </button>
              <button
                onClick={() => testDropoutThreshold(3)}
                className="px-3 py-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/40 text-xs text-red-300 border border-red-800/60"
              >
                Test 3 Dropouts (4 active &lt; k → Safe Abort)
              </button>
            </div>

            {dropoutResult && (
              <div className="mt-4 p-4 rounded-xl bg-slate-800/60 border border-slate-700 font-mono text-xs">
                <div className="text-slate-400 mb-1">Dropout Simulation Output:</div>
                <pre className="text-cyan-300 overflow-x-auto">{JSON.stringify(dropoutResult, null, 2)}</pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Sub-Tab 5: Baseline Comparisons */}
      {activeTab === 'comparison' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-900/40">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-800/60 text-xs font-mono uppercase text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Evaluation Baseline</th>
                  <th className="py-3 px-4">Differential Privacy</th>
                  <th className="py-3 px-4">Secure Aggregation</th>
                  <th className="py-3 px-4">Expected F1</th>
                  <th className="py-3 px-4">Privacy Boundary</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                <tr className="hover:bg-slate-800/30">
                  <td className="py-3 px-4 font-semibold text-white">E6-01: Tenant-Only Local Training</td>
                  <td className="py-3 px-4 text-slate-400">None</td>
                  <td className="py-3 px-4 text-slate-400">N/A (Local)</td>
                  <td className="py-3 px-4 font-mono text-xs">0.24 - 0.72</td>
                  <td className="py-3 px-4 text-xs text-emerald-400">Local Only</td>
                </tr>
                <tr className="hover:bg-slate-800/30">
                  <td className="py-3 px-4 font-semibold text-white">E6-03: Insecure Research FedAvg</td>
                  <td className="py-3 px-4 text-slate-400">None</td>
                  <td className="py-3 px-4 text-slate-400">None</td>
                  <td className="py-3 px-4 font-mono text-xs">0.82 - 0.88</td>
                  <td className="py-3 px-4 text-xs text-amber-400">Plaintext Updates</td>
                </tr>
                <tr className="hover:bg-slate-800/30">
                  <td className="py-3 px-4 font-semibold text-white">E6-05: Federated DP-SGD</td>
                  <td className="py-3 px-4 text-cyan-400">Opacus DP (ε≈2.0)</td>
                  <td className="py-3 px-4 text-slate-400">None</td>
                  <td className="py-3 px-4 font-mono text-xs">0.78 - 0.85</td>
                  <td className="py-3 px-4 text-xs text-cyan-400">DP Record Privacy</td>
                </tr>
                <tr className="hover:bg-slate-800/30 bg-cyan-950/20">
                  <td className="py-3 px-4 font-semibold text-cyan-300">E6-06: Target Protected Profile (DP + SecAgg+)</td>
                  <td className="py-3 px-4 text-cyan-400 font-bold">Opacus DP (ε≈2.0)</td>
                  <td className="py-3 px-4 text-purple-400 font-bold">SecAgg+ (k=5/7)</td>
                  <td className="py-3 px-4 font-mono text-xs text-emerald-400 font-bold">0.83 - 0.91</td>
                  <td className="py-3 px-4 text-xs text-emerald-400 font-bold">DP + Cryptographic Masking</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sub-Tab 6: Governance & Registry */}
      {activeTab === 'governance' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 overflow-hidden bg-slate-900/40">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-800/60 text-xs font-mono uppercase text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Candidate Model ID</th>
                  <th className="py-3 px-4">Protocol</th>
                  <th className="py-3 px-4">Integrity Digest</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {candidates.map((c, i) => (
                  <tr key={i} className="hover:bg-slate-800/30">
                    <td className="py-3 px-4 font-medium text-white">{c.candidate_id || c.model_id}</td>
                    <td className="py-3 px-4 font-mono text-xs text-cyan-400">{c.aggregation_protocol || 'LOCAL'}</td>
                    <td className="py-3 px-4 font-mono text-xs text-slate-400">
                      {((c.model_digest || c.hash || '') as string).slice(0, 16)}...
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-xs font-mono ${
                        c.status === 'ACTIVE'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                          : 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                      }`}>
                        {c.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

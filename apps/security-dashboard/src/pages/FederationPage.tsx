import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import {
  Share2,
  Shield,
  Lock,
  Cpu,
  Activity,
  CheckCircle2,
  RefreshCw,
  Users,
  Play,
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
}

interface Participant {
  participant_id: string;
  name: string;
  data_partition: string;
  connection_status: string;
  cumulative_epsilon: number;
  remaining_epsilon: number;
  eligibility_status: string;
}

interface CandidateModel {
  candidate_id?: string;
  model_id?: string;
  aggregation_protocol?: string;
  model_digest?: string;
  hash?: string;
  status: string;
}

export const FederationPage: React.FC = () => {
  const [status, setStatus] = useState<FederationStatus | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [candidates, setCandidates] = useState<CandidateModel[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'participants' | 'privacy' | 'secagg' | 'comparison' | 'governance'>('overview');
  const [simMessage, setSimMessage] = useState<string | null>(null);
  const [runningSimulation, setRunningSimulation] = useState<boolean>(false);
  const [dropoutResult, setDropoutResult] = useState<any>(null);

  const fetchFederationData = async () => {
    setLoading(true);
    try {
      const [statusRes, partRes, candRes] = await Promise.all([
        api.getFederationStatus().catch(() => null),
        api.getFederationParticipants().catch(() => null),
        api.getFederationModels().catch(() => null),
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
      const data = await api.runFederationSimulation({ profile, partition: 'iid', rounds: 1 });
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
      const data = await api.simulateDropout(dropped);
      setDropoutResult(data);
    } catch (e: any) {
      setDropoutResult({ error: e.message });
    }
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)] gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-cyan-50 border border-cyan-200 flex items-center justify-center text-cyan-700 shrink-0">
            <Share2 className="w-6 h-6" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3 py-0.5 rounded-full text-[11px] font-mono font-bold bg-cyan-50 text-cyan-800 border border-cyan-200">
                PHASE 6 PRIVACY-PRESERVING FL
              </span>
              <span className="px-3 py-0.5 rounded-full text-[11px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                ZERO-COST CPU VERIFIED
              </span>
            </div>
            <h1 className="text-xl font-extrabold text-[#111111] mt-1">
              Federated Learning Operations (FCS-PFL)
            </h1>
            <p className="text-xs text-[#767676] font-medium">
              Privacy-Preserving Threat Intelligence & Multi-ISP Collaborative Defense Architecture v1.2
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => triggerSimulation('protected')}
            disabled={runningSimulation}
            className="px-4 py-2.5 rounded-full bg-[#e60023] hover:bg-[#bd081c] text-white font-bold text-xs flex items-center gap-2 shadow-sm transition disabled:opacity-50 cursor-pointer"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{runningSimulation ? 'Running...' : 'Run Protected FL Round'}</span>
          </button>
          <button
            onClick={fetchFederationData}
            className="p-2.5 rounded-full bg-[#f0f0f2] hover:bg-[#e4e4e7] text-[#111111] transition cursor-pointer"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {simMessage && (
        <div className="p-4 rounded-2xl bg-blue-50 border border-blue-200 text-blue-900 text-xs font-medium flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-blue-600 shrink-0" />
            <span>{simMessage}</span>
          </div>
          <button onClick={() => setSimMessage(null)} className="text-[#767676] hover:text-[#111111] font-bold">✕</button>
        </div>
      )}

      {/* Primary KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="p-5 rounded-3xl bg-white border border-[#ebebeb] shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
          <div className="text-xs font-mono font-bold text-cyan-800 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Federation Status</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-extrabold text-[#111111]">{status?.status || 'OPERATIONAL'}</div>
          <div className="text-xs text-[#767676] mt-2 font-mono font-medium">
            Flower 1.42.0 • SecAgg+ • Opacus
          </div>
        </div>

        <div className="p-5 rounded-3xl bg-white border border-[#ebebeb] shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
          <div className="text-xs font-mono font-bold text-blue-800 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>ISP Cohort</span>
            <Users className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-extrabold text-[#111111]">7 Simulated ISPs</div>
          <div className="text-xs text-[#767676] mt-2 font-mono font-medium">
            Threshold: k=5 of 7 required
          </div>
        </div>

        <div className="p-5 rounded-3xl bg-white border border-[#ebebeb] shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
          <div className="text-xs font-mono font-bold text-purple-800 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Active General Detector</span>
            <Cpu className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-base font-extrabold text-[#111111] truncate" title={status?.active_general_model}>
            {status?.active_general_model || 'lightgbm_deployable'}
          </div>
          <div className="text-xs text-emerald-700 mt-2 font-mono font-bold">
            Bundle Status: {status?.bundle_status || 'ACTIVE'}
          </div>
        </div>

        <div className="p-5 rounded-3xl bg-white border border-[#ebebeb] shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
          <div className="text-xs font-mono font-bold text-emerald-800 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Cost Policy</span>
            <Shield className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-extrabold text-emerald-700">₹0.00 / $0.00</div>
          <div className="text-xs text-[#767676] mt-2 font-mono font-medium">
            Zero Paid Cloud Services
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-zinc-200 pb-2">
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
            className={`px-4 py-2 rounded-full text-xs font-bold transition-all cursor-pointer ${
              activeTab === tab.id
                ? 'bg-[#111111] text-white shadow-sm'
                : 'bg-white text-[#767676] hover:text-[#111111] hover:bg-zinc-100 border border-zinc-200/80'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Sub-Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="p-6 rounded-3xl bg-white border border-[#ebebeb] shadow-[0_2px_12px_rgba(0,0,0,0.03)] space-y-4">
            <h3 className="text-sm font-extrabold text-[#111111] flex items-center space-x-2">
              <Shield className="w-5 h-5 text-indigo-600" />
              <span>Hierarchical Multi-Model Architecture &amp; Isolation Boundaries</span>
            </h3>
            <p className="text-xs text-[#767676] leading-relaxed font-medium">
              FCS-PFL implements collaborative federated learning solely for the <strong className="text-[#111111]">shared general intrusion detection MLP</strong>.
              In strict accordance with FCS Architecture v1.2, <strong className="text-[#111111]">tenant anomaly detectors</strong> (IsolationForest / Autoencoder)
              and specialized threat classifiers (DDoS, Port Scan, Botnet) remain <strong className="text-[#111111]">strictly tenant-local</strong> and are never federated.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              <div className="p-4 rounded-2xl bg-[#f7f7f8] border border-[#ebebeb]">
                <div className="text-[11px] font-mono font-bold text-blue-700 uppercase">Shared Federated Model</div>
                <div className="font-extrabold text-[#111111] text-sm mt-1">PyTorch TabularMLPNet</div>
                <div className="text-xs text-[#767676] mt-1 font-medium">14 deployable NetFlow features, Opacus GroupNorm, binary attack classification.</div>
              </div>
              <div className="p-4 rounded-2xl bg-[#f7f7f8] border border-[#ebebeb]">
                <div className="text-[11px] font-mono font-bold text-purple-700 uppercase">Tenant-Local Anomaly</div>
                <div className="font-extrabold text-[#111111] text-sm mt-1">IsolationForest / Autoencoder</div>
                <div className="text-xs text-[#767676] mt-1 font-medium">Calibrated on private tenant traffic. Kept outside federation to preserve privacy.</div>
              </div>
              <div className="p-4 rounded-2xl bg-[#f7f7f8] border border-[#ebebeb]">
                <div className="text-[11px] font-mono font-bold text-emerald-800 uppercase">Tenant Response Invariant</div>
                <div className="font-extrabold text-[#111111] text-sm mt-1">Manual Response Center</div>
                <div className="text-xs text-[#767676] mt-1 font-medium">AUTO mode permanently disabled. Mitigation requires human operator sign-off.</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sub-Tab 2: Participant Health */}
      {activeTab === 'participants' && (
        <div className="space-y-4">
          <div className="rounded-3xl border border-[#ebebeb] overflow-hidden bg-white shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-zinc-200 text-[11px] font-bold text-[#767676] uppercase tracking-wider bg-[#fafafa]">
                <tr>
                  <th className="py-3 px-4">ISP Participant</th>
                  <th className="py-3 px-4">Partition File</th>
                  <th className="py-3 px-4">Connection</th>
                  <th className="py-3 px-4">Privacy Spent (ε)</th>
                  <th className="py-3 px-4">Remaining (ε)</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 font-mono">
                {participants.map((p) => (
                  <tr key={p.participant_id} className="hover:bg-[#fafafa]">
                    <td className="py-3 px-4 font-bold text-[#111111] flex items-center space-x-2 font-sans">
                      <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                      <span>{p.participant_id}</span>
                      <span className="text-xs text-[#767676] font-normal">({p.name})</span>
                    </td>
                    <td className="py-3 px-4 text-[#767676]">{p.data_partition}</td>
                    <td className="py-3 px-4 text-emerald-700 font-bold">{p.connection_status}</td>
                    <td className="py-3 px-4 text-[#111111]">{p.cumulative_epsilon.toFixed(4)}</td>
                    <td className="py-3 px-4 text-blue-700 font-bold">{p.remaining_epsilon.toFixed(4)}</td>
                    <td className="py-3 px-4 font-sans">
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
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
          <div className="p-6 rounded-3xl bg-white border border-[#ebebeb] shadow-[0_2px_12px_rgba(0,0,0,0.03)] space-y-3">
            <h3 className="text-sm font-extrabold text-[#111111] flex items-center space-x-2">
              <Lock className="w-4 h-4 text-blue-600" />
              <span>Opacus DP-SGD Engine &amp; Cumulative Accounting</span>
            </h3>
            <p className="text-xs text-[#767676] leading-relaxed font-medium">
              Each simulated ISP trains locally using Opacus <code>PrivacyEngine</code> with per-example gradient clipping
              and calibrated Gaussian noise addition. Privacy expenditure is tracked by a durable SQLite state machine
              preventing budget exhaustion or double-spending.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-3 font-mono text-xs">
              <div className="p-4 rounded-2xl bg-[#f7f7f8] border border-[#ebebeb]">
                <div className="text-[#767676] font-sans font-medium">Protected Unit</div>
                <div className="text-blue-700 font-bold mt-1 text-sm">Single Flow Record</div>
              </div>
              <div className="p-4 rounded-2xl bg-[#f7f7f8] border border-[#ebebeb]">
                <div className="text-[#767676] font-sans font-medium">Target Delta (δ)</div>
                <div className="text-blue-700 font-bold mt-1 text-sm">1.0e-05</div>
              </div>
              <div className="p-4 rounded-2xl bg-[#f7f7f8] border border-[#ebebeb]">
                <div className="text-[#767676] font-sans font-medium">Max Grad Norm (C)</div>
                <div className="text-blue-700 font-bold mt-1 text-sm">1.0</div>
              </div>
              <div className="p-4 rounded-2xl bg-[#f7f7f8] border border-[#ebebeb]">
                <div className="text-[#767676] font-sans font-medium">Noise Multiplier (σ)</div>
                <div className="text-blue-700 font-bold mt-1 text-sm">1.1</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sub-Tab 4: Secure Aggregation */}
      {activeTab === 'secagg' && (
        <div className="space-y-6">
          <div className="p-6 rounded-3xl bg-white border border-[#ebebeb] shadow-[0_2px_12px_rgba(0,0,0,0.03)] space-y-4">
            <h3 className="text-sm font-extrabold text-[#111111] flex items-center space-x-2">
              <Lock className="w-4 h-4 text-purple-600" />
              <span>Flower SecAgg+ Protocol Verification (Threshold k=5 of 7)</span>
            </h3>
            <p className="text-xs text-[#767676] leading-relaxed font-medium">
              SecAgg+ coordinates Diffie-Hellman pairwise key agreement, Shamir secret sharing, and pseudo-random
              masking so the central coordinator receives only the sum of parameter vectors, never individual client weights.
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-2">
              <button
                onClick={() => testDropoutThreshold(1)}
                className="px-3.5 py-2 rounded-full bg-white hover:bg-zinc-100 text-xs font-bold text-[#111111] border border-zinc-200 shadow-sm cursor-pointer"
              >
                Test 1 Dropout (6 active → Succeed)
              </button>
              <button
                onClick={() => testDropoutThreshold(2)}
                className="px-3.5 py-2 rounded-full bg-white hover:bg-zinc-100 text-xs font-bold text-[#111111] border border-zinc-200 shadow-sm cursor-pointer"
              >
                Test 2 Dropouts (5 active = k → Succeed)
              </button>
              <button
                onClick={() => testDropoutThreshold(3)}
                className="px-3.5 py-2 rounded-full bg-[#fff0f2] hover:bg-[#ffe4e6] text-xs font-bold text-[#e60023] border border-[#fecdd3] shadow-sm cursor-pointer"
              >
                Test 3 Dropouts (4 active &lt; k → Safe Abort)
              </button>
            </div>

            {dropoutResult && (
              <div className="mt-4 p-4 rounded-2xl bg-[#f7f7f8] border border-[#ebebeb] font-mono text-xs">
                <div className="text-[#111111] font-bold mb-1 font-sans">Dropout Simulation Output:</div>
                <pre className="text-blue-800 overflow-x-auto">{JSON.stringify(dropoutResult, null, 2)}</pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Sub-Tab 5: Baseline Comparisons */}
      {activeTab === 'comparison' && (
        <div className="space-y-4">
          <div className="rounded-3xl border border-[#ebebeb] overflow-hidden bg-white shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-zinc-200 text-[11px] font-bold text-[#767676] uppercase tracking-wider bg-[#fafafa]">
                <tr>
                  <th className="py-3 px-4">Evaluation Baseline</th>
                  <th className="py-3 px-4">Differential Privacy</th>
                  <th className="py-3 px-4">Secure Aggregation</th>
                  <th className="py-3 px-4">Expected F1</th>
                  <th className="py-3 px-4">Privacy Boundary</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                <tr className="hover:bg-[#fafafa]">
                  <td className="py-3 px-4 font-bold text-[#111111]">E6-01: Tenant-Only Local Training</td>
                  <td className="py-3 px-4 text-[#767676]">None</td>
                  <td className="py-3 px-4 text-[#767676]">N/A (Local)</td>
                  <td className="py-3 px-4 font-mono font-bold text-[#111111]">0.24 - 0.72</td>
                  <td className="py-3 px-4">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                      Local Only
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-[#fafafa]">
                  <td className="py-3 px-4 font-bold text-[#111111]">E6-03: Insecure Research FedAvg</td>
                  <td className="py-3 px-4 text-[#767676]">None</td>
                  <td className="py-3 px-4 text-[#767676]">None</td>
                  <td className="py-3 px-4 font-mono font-bold text-[#111111]">0.82 - 0.88</td>
                  <td className="py-3 px-4">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                      Plaintext Updates
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-[#fafafa]">
                  <td className="py-3 px-4 font-bold text-[#111111]">E6-05: Federated DP-SGD</td>
                  <td className="py-3 px-4 text-blue-700 font-medium">Opacus DP (ε≈2.0)</td>
                  <td className="py-3 px-4 text-[#767676]">None</td>
                  <td className="py-3 px-4 font-mono font-bold text-[#111111]">0.78 - 0.85</td>
                  <td className="py-3 px-4">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-800 border border-blue-200">
                      DP Record Privacy
                    </span>
                  </td>
                </tr>
                <tr className="hover:bg-[#fafafa] bg-blue-50/40">
                  <td className="py-3 px-4 font-extrabold text-[#111111]">E6-06: Target Protected Profile (DP + SecAgg+)</td>
                  <td className="py-3 px-4 text-blue-700 font-bold">Opacus DP (ε≈2.0)</td>
                  <td className="py-3 px-4 text-purple-700 font-bold">SecAgg+ (k=5/7)</td>
                  <td className="py-3 px-4 font-mono text-emerald-700 font-bold">0.83 - 0.91</td>
                  <td className="py-3 px-4">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
                      DP + Cryptographic Masking
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sub-Tab 6: Governance & Registry */}
      {activeTab === 'governance' && (
        <div className="space-y-4">
          <div className="rounded-3xl border border-[#ebebeb] overflow-hidden bg-white shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-zinc-200 text-[11px] font-bold text-[#767676] uppercase tracking-wider bg-[#fafafa]">
                <tr>
                  <th className="py-3 px-4">Candidate Model ID</th>
                  <th className="py-3 px-4">Protocol</th>
                  <th className="py-3 px-4">Integrity Digest</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 font-mono">
                {candidates.map((c, i) => (
                  <tr key={i} className="hover:bg-[#fafafa]">
                    <td className="py-3 px-4 font-bold text-[#111111]">{c.candidate_id || c.model_id}</td>
                    <td className="py-3 px-4 text-blue-700">{c.aggregation_protocol || 'LOCAL'}</td>
                    <td className="py-3 px-4 text-[#767676]">
                      {((c.model_digest || c.hash || '') as string).slice(0, 16)}...
                    </td>
                    <td className="py-3 px-4 font-sans">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        c.status === 'ACTIVE'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : 'bg-blue-50 text-blue-800 border border-blue-200'
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

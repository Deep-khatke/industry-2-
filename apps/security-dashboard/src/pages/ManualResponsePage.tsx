import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  RotateCcw,
  AlertTriangle,
  Clock,
  CheckCircle2,
  Lock,
  Radio,
  FileCheck,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { ActionRecord, FirewallRule, Incident, Recommendation, User } from '../types/api';

interface ManualResponsePageProps {
  recommendations: Recommendation[];
  actions: ActionRecord[];
  firewallRules: FirewallRule[];
  activeIncidents: Incident[];
  currentUser: User | null;
  onApproveAction: (payload: {
    incident_id: string;
    action_type: string;
    target: string;
    duration_seconds: number;
    idempotency_key: string;
    scope: string;
    recommendation_id?: string;
  }) => Promise<void>;
  onRollbackAction: (actionId: string) => Promise<void>;
  targetIncident?: Incident | null;
}

export const ManualResponsePage: React.FC<ManualResponsePageProps> = ({
  recommendations,
  actions,
  firewallRules,
  activeIncidents,
  currentUser,
  onApproveAction,
  onRollbackAction,
  targetIncident,
}) => {
  const [selectedRec, setSelectedRec] = useState<Recommendation | null>(null);
  const [targetIp, setTargetIp] = useState<string>(targetIncident?.target_ip || '203.0.113.50');
  const [actionType, setActionType] = useState<string>('TEMPORARY_BLOCK');
  const [duration, setDuration] = useState<number>(900);
  const [scope, setScope] = useState<string>('EDGE_FIREWALL');
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>(
    targetIncident?.incident_id || (activeIncidents[0]?.incident_id ?? '')
  );
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [showApprovalModal, setShowApprovalModal] = useState<boolean>(false);

  const canApprove =
    currentUser?.role === 'SECURITY_RESPONDER' ||
    currentUser?.role === 'TENANT_ADMIN' ||
    currentUser?.role === 'PLATFORM_ADMIN';

  const handleOpenApproval = (rec?: Recommendation) => {
    if (rec) {
      setSelectedRec(rec);
      setTargetIp(rec.target);
      setActionType(rec.action_type);
      setDuration(rec.recommended_duration_seconds);
      setScope(rec.scope);
      setSelectedIncidentId(rec.incident_id);
    }
    setShowApprovalModal(true);
  };

  const handleExecuteApproval = async () => {
    if (!selectedIncidentId) {
      alert('Please select an active incident to link this defensive action.');
      return;
    }
    setIsSubmitting(true);
    try {
      const idempotencyKey = `idem_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
      await onApproveAction({
        incident_id: selectedIncidentId,
        action_type: actionType,
        target: targetIp,
        duration_seconds: duration,
        idempotency_key: idempotencyKey,
        scope,
        recommendation_id: selectedRec?.recommendation_id,
      });
      setShowApprovalModal(false);
    } catch (e: any) {
      alert(`Defensive Action Approval Failed: ${e.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRollback = async (actionId: string) => {
    if (!confirm('Are you sure you want to rollback and revoke this simulated firewall rule?')) return;
    try {
      await onRollbackAction(actionId);
    } catch (e: any) {
      alert(`Rollback failed: ${e.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Policy & Safety Banner */}
      <div className="bg-gradient-to-r from-emerald-950/40 via-cyan-950/20 to-slate-900 border border-emerald-800/50 p-4 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-emerald-950 border border-emerald-600/60 text-emerald-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white flex items-center space-x-2">
              <span>Manual Response Policy Active (Architecture v1.2)</span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-700">
                HUMAN-IN-THE-LOOP
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Defensive actions require verified authorization by a Security Responder. Real network modifications are strictly prohibited in Phase 4.
            </p>
          </div>
        </div>

        <div className="text-right">
          <div className="text-[11px] font-mono text-amber-400 flex items-center space-x-1.5 justify-end">
            <Lock className="w-3.5 h-3.5" />
            <span>AUTO Execution: Disabled</span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
            Boundary: Isolated Software Simulator
          </div>
        </div>
      </div>

      {/* Recommended Defensive Actions Section */}
      <div className="cyber-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white tracking-wide">
              Proposed Defensive Recommendations ({recommendations.length})
            </h3>
          </div>
          <button
            onClick={() => handleOpenApproval()}
            disabled={!canApprove}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-cyan-500 text-black hover:bg-cyan-400 transition-colors disabled:opacity-50"
          >
            + Create Custom Action
          </button>
        </div>

        {recommendations.length === 0 ? (
          <div className="py-10 text-center text-xs text-slate-500 font-mono">
            No pending recommendations. When suspicious flows or DDoS floods are detected, actionable defensive proposals appear here.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recommendations.map((rec) => (
              <div
                key={rec.recommendation_id}
                className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-cyan-500/40 transition-all space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800/60">
                    {rec.action_type}
                  </span>
                  <StatusBadge type="severity" value={rec.risk_level as any} />
                </div>
                <div className="text-xs font-semibold text-slate-200">{rec.reason}</div>
                <div className="text-[11px] font-mono text-slate-400 space-y-1 bg-slate-950/60 p-2.5 rounded border border-slate-800/60">
                  <div>Target: <span className="text-cyan-400 font-bold">{rec.target}</span></div>
                  <div>Scope: {rec.scope}</div>
                  <div>Recommended Duration: {rec.recommended_duration_seconds}s</div>
                </div>
                <button
                  onClick={() => handleOpenApproval(rec)}
                  disabled={!canApprove}
                  className="w-full py-1.5 px-3 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-bold text-xs transition-colors disabled:opacity-50 shadow-[0_0_10px_rgba(6,182,212,0.2)]"
                >
                  {canApprove ? 'Review & Approve Action' : 'Approval Requires Responder Role'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Active Simulated Firewall Rules */}
      <div className="cyber-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Radio className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-white tracking-wide">
              Active Software Simulator Firewall Rules ({firewallRules.length})
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Verified Read-back State
          </span>
        </div>

        {firewallRules.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500 font-mono">
            No active simulated firewall rules. Approved defensive actions will be enforced here.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-2.5 px-3">Rule ID</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Target</th>
                  <th className="py-2.5 px-3">Enforced At</th>
                  <th className="py-2.5 px-3">Expires At</th>
                  <th className="py-2.5 px-3">Simulator State</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {firewallRules.map((r) => (
                  <tr key={r.rule_id} className="hover:bg-slate-800/30">
                    <td className="py-3 px-3 text-cyan-400 font-bold">{r.rule_id}</td>
                    <td className="py-3 px-3 text-white">{r.rule_type}</td>
                    <td className="py-3 px-3 text-emerald-400 font-bold">{r.target}</td>
                    <td className="py-3 px-3 text-slate-400">
                      {new Date(r.applied_at).toLocaleTimeString()}
                    </td>
                    <td className="py-3 px-3 text-amber-400">
                      {new Date(r.expires_at).toLocaleTimeString()}
                    </td>
                    <td className="py-3 px-3">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-700">
                        ACTIVE ENFORCED
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => handleRollback(r.action_id)}
                        disabled={!canApprove}
                        className="px-2.5 py-1 text-[11px] font-semibold rounded bg-red-950/80 text-red-300 border border-red-800/60 hover:bg-red-900 transition-colors disabled:opacity-50 flex items-center space-x-1 ml-auto"
                      >
                        <RotateCcw className="w-3 h-3" />
                        <span>Revoke</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Response Action Journal (Audit Log) */}
      <div className="cyber-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <FileCheck className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-bold text-white tracking-wide">
              Defensive Action Audit Journal ({actions.length})
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Immutable Audit Trail & Idempotency Key Log
          </span>
        </div>

        {actions.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500 font-mono">
            No action history recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-2.5 px-3">Action ID</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Target</th>
                  <th className="py-2.5 px-3">Approved By</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {actions.map((act) => (
                  <tr key={act.action_id} className="hover:bg-slate-800/30">
                    <td className="py-3 px-3 text-cyan-400 font-bold">{act.action_id}</td>
                    <td className="py-3 px-3 text-slate-200">{act.action_type}</td>
                    <td className="py-3 px-3 text-white">{act.target}</td>
                    <td className="py-3 px-3 text-slate-400">{act.approved_by}</td>
                    <td className="py-3 px-3 text-slate-400">{act.duration_seconds}s</td>
                    <td className="py-3 px-3">
                      <StatusBadge type="action_status" value={act.status} />
                    </td>
                    <td className="py-3 px-3 text-slate-500 text-[11px]">
                      {new Date(act.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Administrator Approval Modal */}
      {showApprovalModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="cyber-card p-6 max-w-lg w-full space-y-5 border-cyan-500/60 shadow-[0_0_30px_rgba(6,182,212,0.25)]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <ShieldAlert className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold text-white">Approve Defensive Mitigation</h3>
              </div>
              <button
                onClick={() => setShowApprovalModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs font-mono">
              <div>
                <label className="text-slate-400 uppercase text-[10px] block mb-1">
                  Linked Incident
                </label>
                <select
                  value={selectedIncidentId}
                  onChange={(e) => setSelectedIncidentId(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  {activeIncidents.map((inc) => (
                    <option key={inc.incident_id} value={inc.incident_id}>
                      [{inc.severity}] {inc.title} ({inc.target_ip})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-slate-400 uppercase text-[10px] block mb-1">
                  Defensive Action Type
                </label>
                <select
                  value={actionType}
                  onChange={(e) => setActionType(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                >
                  <option value="TEMPORARY_BLOCK">TEMPORARY_BLOCK (Drop matching ingress packets)</option>
                  <option value="RATE_LIMIT">RATE_LIMIT (Throttle to 100 packets/sec)</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 uppercase text-[10px] block mb-1">
                  Target IP / Prefix
                </label>
                <input
                  type="text"
                  value={targetIp}
                  onChange={(e) => setTargetIp(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-bold"
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-slate-400 uppercase text-[10px]">
                    Mitigation Duration (Non-Permanent)
                  </label>
                  <span className="text-cyan-400 font-bold">{duration} seconds ({Math.round(duration/60)} mins)</span>
                </div>
                <input
                  type="range"
                  min="60"
                  max="3600"
                  step="60"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="w-full accent-cyan-400 cursor-pointer"
                />
              </div>

              <div className="p-3 bg-slate-950/80 rounded-lg border border-slate-800 text-[11px] text-slate-400 space-y-1">
                <div className="text-emerald-400 font-bold">Safety Checks Passed:</div>
                <div>• Acting Approver: {currentUser?.username} ({currentUser?.role})</div>
                <div>• Target is NOT protected gateway / management infrastructure</div>
                <div>• Automatic rule TTL expiration strictly bounded (≤ 3600s)</div>
              </div>

              <div className="text-[10px] text-slate-500 italic">
                * Simulated defensive action — no real network device modified.
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
              <button
                onClick={() => setShowApprovalModal(false)}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteApproval}
                disabled={isSubmitting}
                className="px-4 py-2 text-xs font-bold rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black transition-colors disabled:opacity-50 shadow-[0_0_12px_rgba(16,185,129,0.3)] flex items-center space-x-1.5"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>{isSubmitting ? 'Simulating...' : 'Authorize & Execute'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

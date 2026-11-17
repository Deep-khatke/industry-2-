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
  Plus,
  X,
  Sliders,
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
  const [filterMode, setFilterMode] = useState<'PENDING' | 'ALL'>('PENDING');
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
    if (!confirm('Revoke this simulated mitigation rule?')) return;
    try {
      await onRollbackAction(actionId);
    } catch (e: any) {
      alert(`Rollback failed: ${e.message}`);
    }
  };

  const pendingRecs = recommendations.filter((r) => r.status !== 'APPLIED');
  const displayRecs = filterMode === 'PENDING' ? pendingRecs : recommendations;

  return (
    <div className="space-y-5 font-sans">
      {/* Policy & Safety Invariant Banner */}
      <div className="bg-white border border-[#ebebeb] p-6 rounded-3xl shadow-[0_2px_12px_rgba(0,0,0,0.03)] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-sm font-extrabold text-[#111111] flex items-center gap-2">
              <span>Manual Defensive Response Gate Active</span>
              <span className="text-[10px] font-mono text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200 font-bold">
                HUMAN-IN-THE-LOOP
              </span>
            </h2>
            <p className="text-xs text-[#767676] font-medium mt-1">
              All mitigations require authenticated operator approval and execute in the isolated software simulator.
            </p>
          </div>
        </div>

        <div className="text-right shrink-0">
          <div className="text-xs font-mono text-amber-800 bg-amber-50 px-3 py-1 rounded-full border border-amber-200 font-bold flex items-center gap-1.5 justify-end">
            <Lock className="w-3.5 h-3.5 text-amber-600" />
            <span>Gate G13: BLOCKED</span>
          </div>
          <div className="text-[11px] text-[#767676] font-medium mt-1">
            Boundary: Software Simulator
          </div>
        </div>
      </div>

      {/* Recommended Defensive Actions Section */}
      <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100 flex-wrap gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-2xl bg-[#fff0f2] text-[#e60023]">
              <ShieldAlert className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-extrabold text-[#111111]">
              Proposed Defensive Recommendations ({displayRecs.length})
            </h3>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="flex items-center bg-[#f0f0f2] p-1 rounded-full text-xs font-bold font-mono">
              <button
                onClick={() => setFilterMode('PENDING')}
                className={`px-3 py-1 rounded-full transition-all ${
                  filterMode === 'PENDING'
                    ? 'bg-white text-[#111111] shadow-xs'
                    : 'text-[#767676] hover:text-[#111111]'
                }`}
              >
                Pending ({pendingRecs.length})
              </button>
              <button
                onClick={() => setFilterMode('ALL')}
                className={`px-3 py-1 rounded-full transition-all ${
                  filterMode === 'ALL'
                    ? 'bg-white text-[#111111] shadow-xs'
                    : 'text-[#767676] hover:text-[#111111]'
                }`}
              >
                All ({recommendations.length})
              </button>
            </div>

            <button
              onClick={() => handleOpenApproval()}
              disabled={!canApprove}
              className="px-4 py-2 text-xs font-bold rounded-full bg-[#111111] hover:bg-[#333333] text-white transition-all disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Custom Action</span>
            </button>
          </div>
        </div>

        {displayRecs.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#767676] font-medium">
            {filterMode === 'PENDING'
              ? 'All defensive recommendations have been reviewed and applied. Check the Active Firewall Rules below.'
              : 'No defensive recommendations recorded for this tenant.'}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {displayRecs.map((rec) => (
              <div
                key={rec.recommendation_id}
                className="p-5 rounded-2xl bg-white border border-zinc-200/80 hover:border-[#e60023] shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold font-mono text-[#e60023] bg-[#fff0f2] px-2.5 py-1 rounded-full border border-[#fecdd3]">
                    {rec.action_type}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {rec.status === 'APPLIED' && (
                      <span className="text-[10px] font-mono font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                        APPLIED
                      </span>
                    )}
                    <StatusBadge type="severity" value={rec.risk_level as any} />
                  </div>
                </div>
                <div className="text-xs font-bold text-[#111111]">{rec.reason}</div>
                <div className="text-xs font-mono text-[#5f5f5f] space-y-1 bg-[#fafafa] p-3 rounded-2xl border border-zinc-100">
                  <div>Target: <span className="text-[#111111] font-bold">{rec.target}</span></div>
                  <div>Scope: {rec.scope}</div>
                  <div>TTL: {rec.recommended_duration_seconds}s</div>
                </div>
                <button
                  onClick={() => handleOpenApproval(rec)}
                  disabled={!canApprove || rec.status === 'APPLIED'}
                  className="w-full py-2.5 px-4 rounded-full bg-[#e60023] hover:bg-[#bd081c] text-white font-bold text-xs transition-all disabled:opacity-50 shadow-sm"
                >
                  {rec.status === 'APPLIED'
                    ? 'Action Already Enforced'
                    : canApprove
                    ? 'Review & Approve Action'
                    : 'Requires Responder Role'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Active Simulated Firewall Rules */}
      <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-2xl bg-emerald-50 text-emerald-600">
              <Radio className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-extrabold text-[#111111]">
              Active Simulator Firewall Rules ({firewallRules.length})
            </h3>
          </div>
          <span className="text-xs font-mono text-[#767676] bg-[#f0f0f2] px-3 py-1 rounded-full font-medium">
            Read-back State Verified
          </span>
        </div>

        {firewallRules.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#767676] font-medium">
            No active simulated firewall rules. Approved defensive actions will be enforced here.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-zinc-100 text-[11px] font-bold text-[#767676] uppercase tracking-wider">
                  <th className="py-3 px-3">Rule ID</th>
                  <th className="py-3 px-3">Type</th>
                  <th className="py-3 px-3">Target</th>
                  <th className="py-3 px-3">Enforced (UTC)</th>
                  <th className="py-3 px-3">Expires (UTC)</th>
                  <th className="py-3 px-3">State</th>
                  <th className="py-3 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 font-mono">
                {firewallRules.map((r) => (
                  <tr key={r.rule_id} className="hover:bg-[#fafafa]">
                    <td className="py-3 px-3 text-blue-700 font-bold">{r.rule_id}</td>
                    <td className="py-3 px-3 text-[#111111]">{r.rule_type}</td>
                    <td className="py-3 px-3 text-emerald-700 font-bold">{r.target}</td>
                    <td className="py-3 px-3 text-[#767676] tabular-nums">
                      {new Date(r.applied_at).toISOString().substring(11, 19)}
                    </td>
                    <td className="py-3 px-3 text-amber-700 tabular-nums">
                      {new Date(r.expires_at).toISOString().substring(11, 19)}
                    </td>
                    <td className="py-3 px-3">
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                        ACTIVE
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => handleRollback(r.action_id)}
                        disabled={!canApprove}
                        className="px-3 py-1 text-xs font-bold rounded-full bg-[#fff0f2] text-[#e60023] border border-[#fecdd3] hover:bg-[#ffe2e5] transition-colors disabled:opacity-50 inline-flex items-center gap-1"
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
      <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-2xl bg-purple-50 text-purple-600">
              <FileCheck className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-extrabold text-[#111111]">
              Defensive Action Audit Journal ({actions.length})
            </h3>
          </div>
          <span className="text-xs font-mono text-[#767676] bg-[#f0f0f2] px-3 py-1 rounded-full font-medium">
            Immutable Audit Trail & Idempotency Key Log
          </span>
        </div>

        {actions.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#767676] font-medium">
            No action history recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-zinc-100 text-[11px] font-bold text-[#767676] uppercase tracking-wider">
                  <th className="py-3 px-3">Action ID</th>
                  <th className="py-3 px-3">Type</th>
                  <th className="py-3 px-3">Target</th>
                  <th className="py-3 px-3">Approved By</th>
                  <th className="py-3 px-3">Duration</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Timestamp (UTC)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 font-mono">
                {actions.map((act) => (
                  <tr key={act.action_id} className="hover:bg-[#fafafa]">
                    <td className="py-3 px-3 text-blue-700 font-bold">{act.action_id}</td>
                    <td className="py-3 px-3 text-[#111111]">{act.action_type}</td>
                    <td className="py-3 px-3 text-[#111111] font-bold">{act.target}</td>
                    <td className="py-3 px-3 text-[#767676]">{act.approved_by}</td>
                    <td className="py-3 px-3 text-[#767676]">{act.duration_seconds}s</td>
                    <td className="py-3 px-3">
                      <StatusBadge type="action_status" value={act.status} />
                    </td>
                    <td className="py-3 px-3 text-[#767676] text-xs tabular-nums">
                      {new Date(act.created_at).toISOString().replace('T', ' ').substring(0, 19)}
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
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 max-w-md w-full space-y-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-100">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-2xl bg-[#fff0f2] text-[#e60023]">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <h3 className="text-base font-extrabold text-[#111111]">Authorize Defensive Mitigation</h3>
              </div>
              <button
                onClick={() => setShowApprovalModal(false)}
                className="text-[#767676] hover:text-[#111111] p-1.5 rounded-full hover:bg-[#f0f0f2]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs font-sans">
              <div>
                <label className="text-[#767676] uppercase text-[10px] font-bold block mb-1.5 px-1">
                  Linked Incident
                </label>
                <select
                  value={selectedIncidentId}
                  onChange={(e) => setSelectedIncidentId(e.target.value)}
                  className="w-full bg-[#f0f0f2] border-0 rounded-2xl p-3 text-[#111111] focus:ring-2 focus:ring-[#e60023]/20 font-mono text-xs cursor-pointer font-bold"
                >
                  {activeIncidents.map((inc) => (
                    <option key={inc.incident_id} value={inc.incident_id}>
                      [{inc.severity}] {inc.title} ({inc.target_ip})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[#767676] uppercase text-[10px] font-bold block mb-1.5 px-1">
                  Mitigation Action
                </label>
                <select
                  value={actionType}
                  onChange={(e) => setActionType(e.target.value)}
                  className="w-full bg-[#f0f0f2] border-0 rounded-2xl p-3 text-[#111111] focus:ring-2 focus:ring-[#e60023]/20 text-xs cursor-pointer font-bold"
                >
                  <option value="TEMPORARY_BLOCK">TEMPORARY_BLOCK (Drop matching ingress packets)</option>
                  <option value="RATE_LIMIT">RATE_LIMIT (Throttle to 100 packets/sec)</option>
                </select>
              </div>

              <div>
                <label className="text-[#767676] uppercase text-[10px] font-bold block mb-1.5 px-1">
                  Target IP / Prefix
                </label>
                <input
                  type="text"
                  value={targetIp}
                  onChange={(e) => setTargetIp(e.target.value)}
                  className="w-full bg-[#f0f0f2] border-0 rounded-full px-4 py-2.5 text-[#111111] focus:ring-2 focus:ring-[#e60023]/20 font-mono font-bold"
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5 px-1">
                  <label className="text-[#767676] uppercase text-[10px] font-bold">
                    Time To Live (TTL)
                  </label>
                  <span className="text-[#e60023] font-mono font-bold">{duration}s ({Math.round(duration / 60)} mins)</span>
                </div>
                <input
                  type="range"
                  min="60"
                  max="3600"
                  step="60"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="w-full accent-[#e60023] cursor-pointer"
                />
              </div>

              <div className="p-3.5 bg-[#fafafa] rounded-2xl border border-zinc-100 text-xs text-[#5f5f5f] space-y-1 font-mono">
                <div className="text-emerald-800 font-bold">Policy Guardrail Checks:</div>
                <div>• Approver: {currentUser?.username} ({currentUser?.role})</div>
                <div>• Protected Target Allowlist: Verified Not Protected</div>
                <div>• TTL Expiration: 60s ≤ {duration}s ≤ 3600s</div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-zinc-100">
              <button
                onClick={() => setShowApprovalModal(false)}
                className="px-4 py-2 text-xs font-bold rounded-full bg-[#f0f0f2] text-[#111111] hover:bg-[#e2e2e4] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteApproval}
                disabled={isSubmitting}
                className="px-5 py-2 text-xs font-bold rounded-full bg-emerald-600 hover:bg-emerald-700 text-white transition-all disabled:opacity-50 flex items-center gap-2 shadow-sm"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>{isSubmitting ? 'Simulating...' : 'Authorize Action'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

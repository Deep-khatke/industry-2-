import React, { useState } from 'react';
import {
  AlertTriangle,
  Search,
  CheckCircle,
  XCircle,
  Clock,
  Shield,
  ArrowRight,
  FileText,
  User,
  History,
  X,
  Layers,
  ChevronRight,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { Incident, IncidentHistory, Recommendation } from '../types/api';

interface IncidentsPageProps {
  incidents: Incident[];
  selectedIncident: Incident | null;
  onSelectIncident: (inc: Incident | null) => void;
  onUpdateStatus: (incidentId: string, status: string, notes?: string) => Promise<void>;
  incidentHistory: IncidentHistory[];
  recommendations: Recommendation[];
  onNavigateToResponseWithIncident: (incident: Incident) => void;
}

export const IncidentsPage: React.FC<IncidentsPageProps> = ({
  incidents,
  selectedIncident,
  onSelectIncident,
  onUpdateStatus,
  incidentHistory,
  recommendations,
  onNavigateToResponseWithIncident,
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [actionNotes, setActionNotes] = useState<string>('');
  const [isUpdating, setIsUpdating] = useState<boolean>(false);

  const filtered = incidents.filter((inc) => {
    if (statusFilter !== 'ALL' && inc.status !== statusFilter) return false;
    if (severityFilter !== 'ALL' && inc.severity !== severityFilter) return false;
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      return (
        inc.title.toLowerCase().includes(term) ||
        inc.target_ip.includes(term) ||
        inc.incident_id.toLowerCase().includes(term) ||
        inc.attack_category.toLowerCase().includes(term)
      );
    }
    return true;
  });

  const handleStatusChange = async (newStatus: string) => {
    if (!selectedIncident) return;
    setIsUpdating(true);
    try {
      await onUpdateStatus(selectedIncident.incident_id, newStatus, actionNotes || undefined);
      setActionNotes('');
    } catch (e: any) {
      alert(`Status transition failed: ${e.message}`);
    } finally {
      setIsUpdating(false);
    }
  };

  let evidence: any = {};
  if (selectedIncident?.evidence_json) {
    try {
      evidence = JSON.parse(selectedIncident.evidence_json);
    } catch {
      evidence = {};
    }
  }

  const severities = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

  return (
    <div className="space-y-5 font-sans">
      {/* Top Filter Bar */}
      <div className="bg-white border border-[#ebebeb] p-4 rounded-3xl shadow-[0_2px_12px_rgba(0,0,0,0.03)] flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Pinterest Pill Search Bar */}
          <div className="relative">
            <Search className="w-4 h-4 text-[#767676] absolute left-3.5 top-3" />
            <input
              type="text"
              placeholder="Search target IP, port, vector..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-[#f0f0f2] hover:bg-[#e9e9eb] focus:bg-white border border-transparent focus:border-[#e60023] rounded-full pl-10 pr-4 py-2 text-xs text-[#111111] placeholder-[#767676] font-medium focus:outline-none w-72 transition-colors"
            />
          </div>

          {/* Severity Quick Filters */}
          <div className="flex items-center gap-1.5">
            {severities.map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all ${
                  severityFilter === sev
                    ? 'bg-[#111111] text-white shadow-sm'
                    : 'bg-[#f0f0f2] text-[#767676] hover:text-[#111111]'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        {/* Status Filter Dropdown */}
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-[#f0f0f2] border-0 rounded-full px-4 py-2 text-xs font-bold text-[#111111] focus:outline-none focus:ring-2 focus:ring-[#e60023]/20 cursor-pointer"
          >
            <option value="ALL">All Lifecycle Statuses</option>
            <option value="NEW">NEW</option>
            <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
            <option value="INVESTIGATING">INVESTIGATING</option>
            <option value="ACTION_PENDING">ACTION PENDING</option>
            <option value="MITIGATED">MITIGATED</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="FALSE_POSITIVE">FALSE POSITIVE</option>
          </select>
          <span className="text-xs font-mono font-bold text-[#767676] bg-[#f0f0f2] px-3 py-1.5 rounded-full">
            {filtered.length} Recorded
          </span>
        </div>
      </div>

      {/* Main Grid: Table (Left) + Detail Drawer (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Incidents Table */}
        <div className={`bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)] ${selectedIncident ? 'lg:col-span-7' : 'lg:col-span-12'}`}>
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-zinc-100 text-xs font-bold uppercase tracking-wider text-[#767676]">
            <span>Incident Ledger ({filtered.length})</span>
            <span className="text-xs font-mono lowercase">300s deduplication window</span>
          </div>

          {filtered.length === 0 ? (
            <div className="py-16 text-center text-[#767676] font-medium text-xs">
              No incidents match the active search filter criteria.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-zinc-100 text-[11px] font-bold text-[#767676] uppercase tracking-wider">
                    <th className="py-3 px-3">Severity</th>
                    <th className="py-3 px-3">Target & Vector</th>
                    <th className="py-3 px-3">Confidence</th>
                    <th className="py-3 px-3">Lifecycle</th>
                    <th className="py-3 px-3">Time (UTC)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 text-xs">
                  {filtered.map((inc) => {
                    const isSelected = selectedIncident?.incident_id === inc.incident_id;
                    return (
                      <tr
                        key={inc.incident_id}
                        onClick={() => onSelectIncident(inc)}
                        className={`transition-colors cursor-pointer ${
                          isSelected
                            ? 'bg-[#fff0f2] border-l-4 border-[#e60023]'
                            : 'hover:bg-[#fafafa] border-l-4 border-transparent'
                        }`}
                      >
                        <td className="py-3 px-3">
                          <StatusBadge type="severity" value={inc.severity} />
                        </td>
                        <td className="py-3 px-3">
                          <div className="font-bold text-[#111111]">{inc.title}</div>
                          <div className="text-[11px] font-mono text-[#767676] mt-0.5 flex items-center gap-1.5">
                            <span className="font-semibold text-[#111111]">{inc.target_ip}:{inc.target_port}</span>
                            <span>•</span>
                            <span>{inc.attack_category}</span>
                          </div>
                        </td>
                        <td className="py-3 px-3 font-mono font-bold text-[#111111]">
                          {(inc.risk_score * 100).toFixed(0)}%
                        </td>
                        <td className="py-3 px-3">
                          <StatusBadge type="incident_status" value={inc.status} />
                        </td>
                        <td className="py-3 px-3 font-mono text-[#767676] text-[11px] tabular-nums whitespace-nowrap">
                          {new Date(inc.created_at).toISOString().substring(11, 19)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Forensic Inspection Drawer */}
        {selectedIncident && (
          <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-xl lg:col-span-5 space-y-5">
            {/* Header */}
            <div className="flex items-start justify-between pb-3 border-b border-zinc-100">
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1.5">
                  <StatusBadge type="severity" value={selectedIncident.severity} />
                  <span className="text-[11px] font-mono text-[#767676]">{selectedIncident.incident_id}</span>
                </div>
                <h3 className="text-base font-extrabold text-[#111111] truncate">{selectedIncident.title}</h3>
                <div className="text-xs font-mono text-[#767676] mt-1">
                  Target: <span className="text-[#e60023] font-bold">{selectedIncident.target_ip}:{selectedIncident.target_port}</span>
                </div>
              </div>
              <button
                onClick={() => onSelectIncident(null)}
                className="text-[#767676] hover:text-[#111111] p-1.5 rounded-full hover:bg-[#f0f0f2] transition-colors"
                title="Close drawer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Status & Risk Summary */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-[#fafafa] rounded-2xl border border-zinc-100">
                <span className="text-[#767676] block text-[10px] uppercase font-bold">Lifecycle Status</span>
                <div className="mt-1.5">
                  <StatusBadge type="incident_status" value={selectedIncident.status} />
                </div>
              </div>
              <div className="p-3 bg-[#fafafa] rounded-2xl border border-zinc-100">
                <span className="text-[#767676] block text-[10px] uppercase font-bold">Threat Confidence</span>
                <span className="text-base font-extrabold font-mono text-[#111111] mt-1 block">
                  {(selectedIncident.risk_score * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Hierarchical Detection Evidence Breakdown */}
            <div className="space-y-2.5">
              <div className="text-xs font-bold text-[#111111] uppercase tracking-wider flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#e60023]" />
                <span>Detection Engine Evidence</span>
              </div>
              <div className="p-4 bg-[#fafafa] rounded-2xl border border-zinc-100 text-xs font-mono space-y-2 text-[#333333]">
                <div className="flex justify-between">
                  <span className="text-[#767676]">Rules Triggered:</span>
                  <span className="text-amber-700 font-bold">
                    {evidence.matched_rules?.length ? evidence.matched_rules.join(', ') : 'None'}
                  </span>
                </div>

                {evidence.multi_model_evidence && (
                  <div className="pt-2 border-t border-zinc-200 space-y-1 text-[11px]">
                    <div className="text-[10px] text-[#767676] font-bold uppercase">Multi-Model Score Attribution</div>
                    {evidence.multi_model_evidence.general_score && (
                      <div className="flex justify-between">
                        <span className="text-[#767676]">General Threat Detector:</span>
                        <span className="text-blue-700 font-bold">
                          {(evidence.multi_model_evidence.general_score.calibrated_probability * 100).toFixed(1)}%
                        </span>
                      </div>
                    )}
                    {evidence.multi_model_evidence.anomaly_score && (
                      <div className="flex justify-between">
                        <span className="text-[#767676]">Tenant Anomaly Detector:</span>
                        <span className="text-emerald-700 font-bold">
                          {(evidence.multi_model_evidence.anomaly_score.calibrated_probability * 100).toFixed(1)}%
                        </span>
                      </div>
                    )}
                    {evidence.multi_model_evidence.fusion_method && (
                      <div className="flex justify-between text-[10px] text-[#767676] pt-1">
                        <span>Evidence Fusion Mode:</span>
                        <span className="text-[#111111] font-bold">{evidence.multi_model_evidence.fusion_method}</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex justify-between pt-1 border-t border-zinc-200 text-[10px] text-[#767676]">
                  <span>First Observed:</span>
                  <span>{new Date(selectedIncident.created_at).toISOString().replace('T', ' ').substring(0, 19)} UTC</span>
                </div>
              </div>
            </div>

            {/* Recommended Defensive Mitigation */}
            {recommendations.length > 0 && (
              <div className="p-4 rounded-3xl bg-[#fff0f2] border border-[#fecdd3] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#111111] flex items-center gap-1.5">
                    <Shield className="w-4 h-4 text-[#e60023]" />
                    <span>Recommended Mitigation</span>
                  </span>
                  <span className="text-[10px] font-mono text-[#e60023] bg-white px-2.5 py-0.5 rounded-full border border-[#fecdd3] font-bold">
                    {recommendations[0].action_type}
                  </span>
                </div>
                <p className="text-xs text-[#5f5f5f] font-medium">{recommendations[0].reason}</p>
                <div className="flex justify-between items-center text-[10px] font-mono text-[#767676]">
                  <span>Scope: {recommendations[0].scope}</span>
                  <span>TTL: {recommendations[0].recommended_duration_seconds}s</span>
                </div>
                <button
                  onClick={() => onNavigateToResponseWithIncident(selectedIncident)}
                  className="w-full mt-2 py-2.5 px-4 bg-[#e60023] hover:bg-[#bd081c] text-white font-bold text-xs rounded-full transition-all flex items-center justify-center gap-2 shadow-sm"
                >
                  <span>Review & Execute in Response Console</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* Disposition Status Transition Controls */}
            <div className="space-y-3 pt-3 border-t border-zinc-100">
              <label className="text-xs font-bold text-[#111111] uppercase tracking-wider block">
                Update Incident Lifecycle
              </label>
              <input
                type="text"
                placeholder="Disposition notes (optional)..."
                value={actionNotes}
                onChange={(e) => setActionNotes(e.target.value)}
                className="w-full bg-[#f0f0f2] focus:bg-white border border-transparent focus:border-[#e60023] rounded-full px-4 py-2 text-xs text-[#111111] placeholder-[#767676] font-medium focus:outline-none transition-colors"
              />
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  onClick={() => handleStatusChange('ACKNOWLEDGED')}
                  disabled={isUpdating}
                  className="px-3 py-2 text-xs font-bold rounded-full bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors disabled:opacity-50"
                >
                  Acknowledge
                </button>
                <button
                  onClick={() => handleStatusChange('INVESTIGATING')}
                  disabled={isUpdating}
                  className="px-3 py-2 text-xs font-bold rounded-full bg-purple-50 text-purple-700 hover:bg-purple-100 transition-colors disabled:opacity-50"
                >
                  Investigate
                </button>
                <button
                  onClick={() => handleStatusChange('RESOLVED')}
                  disabled={isUpdating}
                  className="px-3 py-2 text-xs font-bold rounded-full bg-emerald-50 text-emerald-800 hover:bg-emerald-100 transition-colors disabled:opacity-50"
                >
                  Resolve
                </button>
                <button
                  onClick={() => handleStatusChange('FALSE_POSITIVE')}
                  disabled={isUpdating}
                  className="px-3 py-2 text-xs font-bold rounded-full bg-zinc-100 text-zinc-700 hover:bg-zinc-200 transition-colors disabled:opacity-50"
                >
                  False Positive
                </button>
              </div>
            </div>

            {/* Audit History Timeline */}
            <div className="space-y-2 pt-3 border-t border-zinc-100">
              <div className="text-xs font-bold text-[#767676] uppercase tracking-wider flex items-center gap-1.5">
                <History className="w-4 h-4" />
                <span>Audit Timeline ({incidentHistory.length})</span>
              </div>
              <div className="max-h-36 overflow-y-auto space-y-2 pr-1">
                {incidentHistory.length === 0 ? (
                  <div className="text-xs text-[#767676] font-medium">No lifecycle transitions recorded yet.</div>
                ) : (
                  incidentHistory.map((h) => (
                    <div
                      key={h.history_id}
                      className="p-3 rounded-2xl bg-[#fafafa] border border-zinc-100 text-xs space-y-1 font-mono"
                    >
                      <div className="flex justify-between text-[#767676]">
                        <span className="font-bold text-[#111111]">{h.previous_status} → {h.new_status}</span>
                        <span>{new Date(h.created_at).toISOString().substring(11, 19)} UTC</span>
                      </div>
                      {h.change_notes && <div className="text-[#5f5f5f]">{h.change_notes}</div>}
                      <div className="text-[10px] text-[#767676]">Actor: {h.actor_id}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

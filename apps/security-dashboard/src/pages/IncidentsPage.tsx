import React, { useState } from 'react';
import {
  AlertTriangle,
  Search,
  Filter,
  CheckCircle,
  XCircle,
  Clock,
  Shield,
  ArrowRight,
  FileText,
  User,
  History,
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
        inc.incident_id.toLowerCase().includes(term)
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

  return (
    <div className="space-y-6">
      {/* Top Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-[#0d131f] border border-slate-800 p-4 rounded-xl">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-red-950/60 border border-red-700/60 text-red-400">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Incident Management & Disposition</h2>
            <p className="text-xs text-slate-400">
              Persistent incident storage with 300s deduplication windows and full audit trail.
            </p>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search title, IP, ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-44"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="NEW">NEW</option>
            <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
            <option value="INVESTIGATING">INVESTIGATING</option>
            <option value="ACTION_PENDING">ACTION PENDING</option>
            <option value="MITIGATED">MITIGATED</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="FALSE_POSITIVE">FALSE POSITIVE</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
        </div>
      </div>

      {/* Main Grid: Table (Left) + Detail Drawer (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Incidents Table */}
        <div className={`cyber-card p-5 ${selectedIncident ? 'lg:col-span-7' : 'lg:col-span-12'}`}>
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Recorded Incidents ({filtered.length})
            </span>
            <span className="text-xs font-mono text-slate-500">
              Deduplication Window: 300s
            </span>
          </div>

          {filtered.length === 0 ? (
            <div className="py-16 text-center text-slate-500 font-mono text-xs">
              No incidents matching active filters.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    <th className="py-2.5 px-3">Sev</th>
                    <th className="py-2.5 px-3">Incident</th>
                    <th className="py-2.5 px-3">Risk</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-xs">
                  {filtered.map((inc) => {
                    const isSelected = selectedIncident?.incident_id === inc.incident_id;
                    return (
                      <tr
                        key={inc.incident_id}
                        onClick={() => onSelectIncident(inc)}
                        className={`transition-colors cursor-pointer ${
                          isSelected
                            ? 'bg-cyan-950/40 border-l-2 border-cyan-400'
                            : 'hover:bg-slate-800/40'
                        }`}
                      >
                        <td className="py-3 px-3">
                          <StatusBadge type="severity" value={inc.severity} />
                        </td>
                        <td className="py-3 px-3">
                          <div className="font-semibold text-slate-200">{inc.title}</div>
                          <div className="text-[11px] font-mono text-cyan-400">
                            {inc.target_ip}:{inc.target_port} • {inc.attack_category}
                          </div>
                        </td>
                        <td className="py-3 px-3 font-mono font-bold text-white">
                          {(inc.risk_score * 100).toFixed(0)}%
                        </td>
                        <td className="py-3 px-3">
                          <StatusBadge type="incident_status" value={inc.status} />
                        </td>
                        <td className="py-3 px-3 font-mono text-slate-400 text-[11px] whitespace-nowrap">
                          {new Date(inc.created_at).toLocaleTimeString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Incident Detail Drawer */}
        {selectedIncident && (
          <div className="cyber-card p-5 lg:col-span-5 space-y-5 border-cyan-500/40">
            {/* Header */}
            <div className="flex items-start justify-between pb-3 border-b border-slate-800">
              <div>
                <div className="flex items-center space-x-2 mb-1">
                  <StatusBadge type="severity" value={selectedIncident.severity} />
                  <span className="text-xs font-mono text-slate-500">{selectedIncident.incident_id}</span>
                </div>
                <h3 className="text-base font-bold text-white">{selectedIncident.title}</h3>
                <div className="text-xs font-mono text-cyan-400 mt-1">
                  Target: {selectedIncident.target_ip}:{selectedIncident.target_port}
                </div>
              </div>
              <button
                onClick={() => onSelectIncident(null)}
                className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800"
              >
                ✕
              </button>
            </div>

            {/* Current Status & Risk */}
            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800">
                <span className="text-slate-500 block text-[10px]">CURRENT STATUS</span>
                <div className="mt-1">
                  <StatusBadge type="incident_status" value={selectedIncident.status} />
                </div>
              </div>
              <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800">
                <span className="text-slate-500 block text-[10px]">CALCULATED RISK</span>
                <span className="text-base font-bold text-cyan-400 mt-1 block">
                  {(selectedIncident.risk_score * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Supporting Evidence Breakdown */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                <FileText className="w-3.5 h-3.5 text-cyan-400" />
                <span>Hierarchical Detection Evidence (FCS-HMD)</span>
              </h4>
              <div className="p-3 bg-slate-950/70 rounded-lg border border-slate-800/80 text-xs font-mono space-y-2 text-slate-300">
                <div>
                  <span className="text-slate-500">Grouping Key: </span>
                  <span className="text-slate-300 break-all">{selectedIncident.grouping_key}</span>
                </div>
                <div>
                  <span className="text-slate-500">Rules Triggered: </span>
                  <span className="text-purple-400">
                    {evidence.matched_rules?.length ? evidence.matched_rules.join(', ') : 'None'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Composite Risk Score: </span>
                  <span className="text-cyan-400 font-bold">
                    {(selectedIncident.risk_score * 100).toFixed(1)}%
                  </span>
                </div>

                {/* Multi-Model Breakdown if available */}
                {evidence.multi_model_evidence && (
                  <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
                    <div className="text-[10px] text-cyan-300 font-bold uppercase tracking-wider">
                      Multi-Model Score Attribution
                    </div>
                    {evidence.multi_model_evidence.general_score && (
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-400">General Threat Detector:</span>
                        <span className="text-cyan-300">
                          {(evidence.multi_model_evidence.general_score.calibrated_probability * 100).toFixed(1)}% ({evidence.multi_model_evidence.general_score.status})
                        </span>
                      </div>
                    )}
                    {evidence.multi_model_evidence.anomaly_score && (
                      <div className="flex justify-between text-[11px]">
                        <span className="text-slate-400">Tenant Anomaly Detector:</span>
                        <span className="text-emerald-300">
                          {(evidence.multi_model_evidence.anomaly_score.calibrated_probability * 100).toFixed(1)}% ({evidence.multi_model_evidence.anomaly_score.status})
                        </span>
                      </div>
                    )}
                    {evidence.multi_model_evidence.specialist_scores?.map((sp: any) => (
                      <div key={sp.model_id} className="flex justify-between text-[11px]">
                        <span className="text-slate-400">Specialist ({sp.predicted_label || sp.model_id}):</span>
                        <span className={sp.prediction === 1 ? "text-amber-400 font-bold" : "text-slate-400"}>
                          {(sp.calibrated_probability * 100).toFixed(1)}% ({sp.status})
                        </span>
                      </div>
                    ))}
                    {evidence.multi_model_evidence.fusion_method && (
                      <div className="flex justify-between text-[10px] text-slate-500 pt-1">
                        <span>Fusion Mode:</span>
                        <span className="text-purple-300 font-bold">{evidence.multi_model_evidence.fusion_method}</span>
                      </div>
                    )}
                  </div>
                )}

                <div>
                  <span className="text-slate-500">First Detected: </span>
                  <span>{new Date(selectedIncident.created_at).toLocaleString()}</span>
                </div>
              </div>
            </div>

            {/* Recommended Defensive Action */}
            {recommendations.length > 0 && (
              <div className="p-3 rounded-lg bg-cyan-950/30 border border-cyan-800/40 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-cyan-300 uppercase tracking-wider flex items-center space-x-1">
                    <Shield className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Recommended Defense</span>
                  </span>
                  <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-700/60">
                    {recommendations[0].action_type}
                  </span>
                </div>
                <p className="text-xs text-slate-300">{recommendations[0].reason}</p>
                <div className="flex justify-between items-center pt-1 text-[11px] font-mono text-slate-400">
                  <span>Scope: {recommendations[0].scope}</span>
                  <span>Duration: {recommendations[0].recommended_duration_seconds}s</span>
                </div>
                <button
                  onClick={() => onNavigateToResponseWithIncident(selectedIncident)}
                  className="w-full mt-2 py-2 px-3 bg-cyan-500 hover:bg-cyan-400 text-black font-bold text-xs rounded-lg transition-colors flex items-center justify-center space-x-1.5 shadow-[0_0_12px_rgba(6,182,212,0.3)]"
                >
                  <span>Review & Approve in Response Center</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {/* Disposition Status Transition Controls */}
            <div className="space-y-2 pt-2 border-t border-slate-800">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                Update Disposition
              </label>
              <input
                type="text"
                placeholder="Disposition notes (optional)..."
                value={actionNotes}
                onChange={(e) => setActionNotes(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  onClick={() => handleStatusChange('ACKNOWLEDGED')}
                  disabled={isUpdating}
                  className="px-2.5 py-1.5 text-xs font-semibold rounded bg-indigo-950/80 text-indigo-300 border border-indigo-700 hover:bg-indigo-900 transition-colors disabled:opacity-50"
                >
                  Acknowledge
                </button>
                <button
                  onClick={() => handleStatusChange('INVESTIGATING')}
                  disabled={isUpdating}
                  className="px-2.5 py-1.5 text-xs font-semibold rounded bg-purple-950/80 text-purple-300 border border-purple-700 hover:bg-purple-900 transition-colors disabled:opacity-50"
                >
                  Investigate
                </button>
                <button
                  onClick={() => handleStatusChange('RESOLVED')}
                  disabled={isUpdating}
                  className="px-2.5 py-1.5 text-xs font-semibold rounded bg-emerald-950/80 text-emerald-300 border border-emerald-700 hover:bg-emerald-900 transition-colors disabled:opacity-50"
                >
                  Resolve
                </button>
                <button
                  onClick={() => handleStatusChange('FALSE_POSITIVE')}
                  disabled={isUpdating}
                  className="px-2.5 py-1.5 text-xs font-semibold rounded bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700 transition-colors disabled:opacity-50"
                >
                  False Positive
                </button>
              </div>
            </div>

            {/* Audit History Timeline */}
            <div className="space-y-2 pt-2 border-t border-slate-800">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                <History className="w-3.5 h-3.5 text-slate-400" />
                <span>Audit Timeline ({incidentHistory.length})</span>
              </h4>
              <div className="max-h-40 overflow-y-auto space-y-2 pr-1">
                {incidentHistory.length === 0 ? (
                  <div className="text-[11px] text-slate-500 font-mono">No status changes recorded yet.</div>
                ) : (
                  incidentHistory.map((h) => (
                    <div
                      key={h.history_id}
                      className="p-2 rounded bg-slate-900/60 border border-slate-800 text-[11px] space-y-1 font-mono"
                    >
                      <div className="flex justify-between text-slate-400">
                        <span className="font-bold text-white">{h.previous_status} → {h.new_status}</span>
                        <span>{new Date(h.created_at).toLocaleTimeString()}</span>
                      </div>
                      <div className="text-slate-400">{h.change_notes}</div>
                      <div className="text-[10px] text-slate-500">Actor: {h.actor_id}</div>
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

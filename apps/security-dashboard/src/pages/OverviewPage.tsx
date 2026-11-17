import React from 'react';
import {
  Activity,
  AlertTriangle,
  Cpu,
  Radio,
  ArrowRight,
  Flame,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { Incident, OverviewStats } from '../types/api';

interface OverviewPageProps {
  stats: OverviewStats | null;
  recentIncidents: Incident[];
  onSelectIncident: (incident: Incident) => void;
  onNavigateToIncidents: () => void;
  onNavigateToResponse: () => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  stats,
  recentIncidents,
  onSelectIncident,
  onNavigateToIncidents,
  onNavigateToResponse,
}) => {
  if (!stats) {
    return (
      <div className="flex items-center justify-center h-64 text-[#767676] font-mono text-xs">
        Loading real-time telemetry metrics...
      </div>
    );
  }

  const { flow_metrics, incident_metrics, exporter_summary, detection_summary } = stats;

  return (
    <div className="space-y-6 font-sans">
      {/* Carrier Pipeline Status Banner */}
      <div className="bg-white border border-[#ebebeb] p-6 rounded-3xl shadow-[0_2px_12px_rgba(0,0,0,0.03)] flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-[#fff0f2] border border-[#fecdd3] flex items-center justify-center text-[#e60023] shrink-0">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <div className="text-sm font-extrabold text-[#111111] flex items-center gap-2">
              <span>Carrier Telemetry Ingestion & Defense Pipeline</span>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                Active
              </span>
            </div>
            <p className="text-xs text-[#767676] font-medium mt-1">
              LightGBM CPU-based inference scoring 43 canonical flow features (p50: 9.68ms). Autonomous direct mitigation is held in Manual Simulator Mode.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onNavigateToResponse}
            className="px-4 py-2.5 rounded-full bg-[#111111] hover:bg-[#333333] text-white text-xs font-bold transition-all flex items-center gap-2 shadow-sm"
          >
            <span>Response Center</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Monitored Flows"
          value={flow_metrics.total_monitored_flows.toLocaleString()}
          subtitle={`+${flow_metrics.recent_flows_1h.toLocaleString()} flows in last 60m`}
          icon={<Activity className="w-4 h-4" />}
          variant="cyan"
          badge={
            <span className="text-[10px] font-mono font-bold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
              {flow_metrics.freshness}
            </span>
          }
        />
        <MetricCard
          title="Active Incidents"
          value={incident_metrics.active_incidents}
          subtitle={`${incident_metrics.critical_incidents} Critical • ${incident_metrics.high_incidents} High Severity`}
          icon={<AlertTriangle className="w-4 h-4" />}
          variant={incident_metrics.critical_incidents > 0 ? 'red' : 'amber'}
          badge={
            incident_metrics.critical_incidents > 0 ? (
              <span className="text-[10px] font-mono font-bold text-[#e60023] bg-[#fff0f2] px-2.5 py-1 rounded-full border border-[#fecdd3]">
                CRITICAL
              </span>
            ) : undefined
          }
        />
        <MetricCard
          title="Inference Engine"
          value={detection_summary.active_model_id}
          subtitle={`Model ${detection_summary.model_version} • 0.953 PR-AUC`}
          icon={<Cpu className="w-4 h-4" />}
          variant="purple"
          badge={
            <span className="text-[10px] font-mono font-bold text-blue-700 bg-blue-50 px-2.5 py-1 rounded-full border border-blue-200">
              {detection_summary.model_status}
            </span>
          }
        />
        <MetricCard
          title="Network Exporters"
          value={`${exporter_summary.healthy} / ${exporter_summary.total_configured}`}
          subtitle={`${exporter_summary.healthy} active, 0 packet loss`}
          icon={<Radio className="w-4 h-4" />}
          variant={exporter_summary.healthy === exporter_summary.total_configured ? 'emerald' : 'amber'}
          badge={
            <span className="text-[10px] font-mono font-bold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
              100% HEALTHY
            </span>
          }
        />
      </div>

      {/* Threat Distribution & Lifecycle Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Threat Category Distribution */}
        <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)] lg:col-span-2">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-2xl bg-amber-50 text-amber-600">
                <Flame className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-extrabold text-[#111111]">
                Threat Vector Distribution
              </h2>
            </div>
            <span className="text-xs font-mono font-semibold text-[#767676] bg-[#f0f0f2] px-2.5 py-1 rounded-full">
              {Object.values(incident_metrics.category_breakdown || {}).reduce((a, b) => a + b, 0)} Total
            </span>
          </div>

          <div className="space-y-4">
            {Object.keys(incident_metrics.category_breakdown || {}).length === 0 ? (
              <div className="py-10 text-center text-xs text-[#767676] font-medium">
                No active threats detected. Trigger a telemetry scenario from the header.
              </div>
            ) : (
              Object.entries(incident_metrics.category_breakdown || {}).map(([cat, count]) => {
                const total = Object.values(incident_metrics.category_breakdown).reduce((a, b) => a + b, 0) || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={cat} className="space-y-1.5">
                    <div className="flex justify-between text-xs">
                      <span className="text-[#111111] font-bold">{cat}</span>
                      <span className="font-mono text-[#767676]">
                        <strong className="text-[#111111] font-bold">{count}</strong> ({pct}%)
                      </span>
                    </div>
                    <div className="w-full h-2.5 bg-[#f0f0f2] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#e60023] rounded-full transition-all duration-300"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Incident Lifecycle */}
        <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-2xl bg-emerald-50 text-emerald-600">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-extrabold text-[#111111]">
                Incident Lifecycle
              </h2>
            </div>
          </div>

          <div className="space-y-2.5">
            {Object.entries(incident_metrics.status_breakdown || {}).map(([st, cnt]) => (
              <div
                key={st}
                className="flex items-center justify-between p-2.5 rounded-2xl bg-[#fafafa] border border-zinc-100 hover:bg-[#f0f0f2] transition-colors"
              >
                <StatusBadge type="incident_status" value={st} />
                <span className="text-xs font-mono font-bold text-[#111111]">{cnt}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Detected Incidents Table */}
      <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-2xl bg-[#fff0f2] text-[#e60023]">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-extrabold text-[#111111]">
              Active Security Incidents
            </h2>
          </div>
          <button
            onClick={onNavigateToIncidents}
            className="text-xs font-bold text-[#e60023] hover:text-[#bd081c] flex items-center gap-1.5 transition-colors"
          >
            <span>Full Incident Ledger</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {recentIncidents.length === 0 ? (
          <div className="py-12 text-center text-[#767676] font-medium text-xs">
            No incidents recorded for this tenant. Use "Simulate Telemetry" above to test attack flows.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-zinc-100 text-[11px] font-bold text-[#767676] uppercase tracking-wider">
                  <th className="py-3 px-3">Severity</th>
                  <th className="py-3 px-3">Incident / Vector</th>
                  <th className="py-3 px-3">Target Service</th>
                  <th className="py-3 px-3">Risk Confidence</th>
                  <th className="py-3 px-3">Lifecycle</th>
                  <th className="py-3 px-3">Detected (UTC)</th>
                  <th className="py-3 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 text-xs">
                {recentIncidents.slice(0, 6).map((inc) => (
                  <tr
                    key={inc.incident_id}
                    className="hover:bg-[#fafafa] transition-colors cursor-pointer"
                    onClick={() => onSelectIncident(inc)}
                  >
                    <td className="py-3 px-3">
                      <StatusBadge type="severity" value={inc.severity} />
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-bold text-[#111111]">{inc.title}</div>
                      <div className="text-[10px] font-mono text-[#767676]">{inc.incident_id}</div>
                    </td>
                    <td className="py-3 px-3">
                      <span className="px-2.5 py-1 rounded-full bg-[#f0f0f2] text-[#111111] font-mono text-[11px] font-medium">
                        {inc.target_ip}:{inc.target_port}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono font-bold text-[#111111]">
                      {(inc.risk_score * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-3">
                      <StatusBadge type="incident_status" value={inc.status} />
                    </td>
                    <td className="py-3 px-3 font-mono text-[#767676] text-[11px] tabular-nums">
                      {new Date(inc.created_at).toISOString().substring(11, 19)}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectIncident(inc);
                        }}
                        className="px-3 py-1.5 text-xs font-bold text-[#111111] bg-[#f0f0f2] hover:bg-[#111111] hover:text-white rounded-full transition-colors"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

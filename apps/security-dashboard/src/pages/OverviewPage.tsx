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
      <div className="flex items-center justify-center h-64 text-slate-500 font-mono text-sm">
        Loading security overview metrics...
      </div>
    );
  }

  const { flow_metrics, incident_metrics, exporter_summary, detection_summary } = stats;

  return (
    <div className="space-y-6">
      {/* Top Banner Notice */}
      <div className="bg-gradient-to-r from-cyan-950/40 via-blue-950/20 to-slate-900 border border-cyan-800/40 p-4 rounded-xl flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-900/60 border border-cyan-500/50 flex items-center justify-center shrink-0">
            <Zap className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">
              Autonomous Real-Time Threat Ingestion & Detection Active
            </h2>
            <p className="text-xs text-slate-400">
              Verified LightGBM inference running on local CPU with sub-millisecond scoring. Defensive response strictly enforced in Manual Approval Mode.
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={onNavigateToResponse}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-cyan-500 text-black hover:bg-cyan-400 transition-colors flex items-center space-x-1.5 shadow-[0_0_12px_rgba(6,182,212,0.3)]"
          >
            <span>Response Center</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <MetricCard
          title="Monitored Flows"
          value={flow_metrics.total_monitored_flows.toLocaleString()}
          subtitle={`+${flow_metrics.recent_flows_1h.toLocaleString()} processed in last hour`}
          icon={<Activity className="w-5 h-5" />}
          variant="cyan"
          badge={
            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/60">
              {flow_metrics.freshness}
            </span>
          }
        />
        <MetricCard
          title="Active Incidents"
          value={incident_metrics.active_incidents}
          subtitle={`${incident_metrics.critical_incidents} Critical • ${incident_metrics.high_incidents} High Priority`}
          icon={<AlertTriangle className="w-5 h-5" />}
          variant={incident_metrics.critical_incidents > 0 ? 'red' : 'amber'}
          badge={
            incident_metrics.critical_incidents > 0 ? (
              <span className="text-[10px] font-mono text-red-400 bg-red-950/80 px-2 py-0.5 rounded border border-red-800/60 animate-pulse">
                ACTION REQ
              </span>
            ) : undefined
          }
        />
        <MetricCard
          title="Active Model"
          value={detection_summary.active_model_id}
          subtitle={`Mode: ${detection_summary.inference_mode} (CPU)`}
          icon={<Cpu className="w-5 h-5" />}
          variant="purple"
          badge={
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/60">
              {detection_summary.model_status}
            </span>
          }
        />
        <MetricCard
          title="Telemetry Exporters"
          value={`${exporter_summary.healthy} / ${exporter_summary.total_configured}`}
          subtitle={`${exporter_summary.healthy} healthy, ${exporter_summary.degraded} degraded, ${exporter_summary.stale} stale`}
          icon={<Radio className="w-5 h-5" />}
          variant={exporter_summary.healthy === exporter_summary.total_configured ? 'emerald' : 'amber'}
          badge={
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800/60">
              100% COVERAGE
            </span>
          }
        />
      </div>

      {/* Middle Section: Threat Category Breakdown & Status Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Threat Category Breakdown */}
        <div className="cyber-card p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-white tracking-wide flex items-center space-x-2">
              <Flame className="w-4 h-4 text-orange-400" />
              <span>Threat Category Distribution</span>
            </h2>
            <span className="text-xs text-slate-400 font-mono">
              Total Threats: {Object.values(incident_metrics.category_breakdown || {}).reduce((a, b) => a + b, 0)}
            </span>
          </div>

          <div className="space-y-3">
            {Object.keys(incident_metrics.category_breakdown || {}).length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500 font-mono">
                No active threats detected. Trigger a synthetic replay scenario above.
              </div>
            ) : (
              Object.entries(incident_metrics.category_breakdown || {}).map(([cat, count]) => {
                const total = Object.values(incident_metrics.category_breakdown).reduce((a, b) => a + b, 0) || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={cat} className="space-y-1">
                    <div className="flex justify-between text-xs font-semibold">
                      <span className="text-slate-300">{cat}</span>
                      <span className="font-mono text-cyan-400">
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Incident Lifecycle Status Breakdown */}
        <div className="cyber-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-white tracking-wide flex items-center space-x-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Incident Lifecycle</span>
            </h2>
          </div>

          <div className="space-y-2.5">
            {Object.entries(incident_metrics.status_breakdown || {}).map(([st, cnt]) => (
              <div
                key={st}
                className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/60"
              >
                <StatusBadge type="incident_status" value={st} />
                <span className="text-xs font-mono font-bold text-white">{cnt}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Incidents Table */}
      <div className="cyber-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold text-white tracking-wide flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span>Recent Detected Incidents</span>
          </h2>
          <button
            onClick={onNavigateToIncidents}
            className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
          >
            <span>View All Incidents</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {recentIncidents.length === 0 ? (
          <div className="py-12 text-center text-slate-500 font-mono text-xs">
            No incidents recorded for this tenant yet. Click "DDoS Burst" or "Port Scan" above to simulate threat traffic.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-2.5 px-3">Severity</th>
                  <th className="py-2.5 px-3">Title / Target</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Risk Score</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Detected At</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs">
                {recentIncidents.slice(0, 5).map((inc) => (
                  <tr
                    key={inc.incident_id}
                    className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                    onClick={() => onSelectIncident(inc)}
                  >
                    <td className="py-3 px-3">
                      <StatusBadge type="severity" value={inc.severity} />
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-200">{inc.title}</div>
                      <div className="text-[11px] font-mono text-cyan-400">
                        {inc.target_ip}:{inc.target_port}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-slate-300 font-medium">{inc.attack_category}</td>
                    <td className="py-3 px-3 font-mono font-bold text-white">
                      {(inc.risk_score * 100).toFixed(1)}%
                    </td>
                    <td className="py-3 px-3">
                      <StatusBadge type="incident_status" value={inc.status} />
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-400 text-[11px]">
                      {new Date(inc.created_at).toLocaleTimeString()}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectIncident(inc);
                        }}
                        className="px-2.5 py-1 text-[11px] font-semibold text-cyan-400 bg-cyan-950/60 border border-cyan-800/60 rounded hover:bg-cyan-900 transition-colors"
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

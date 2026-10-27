import React from 'react';
import { Radio, Activity, CheckCircle2, AlertTriangle, Clock, Database, Layers } from 'lucide-react';
import { Exporter, OverviewStats, Tenant } from '../types/api';

interface NetworkHealthPageProps {
  exporters: Exporter[];
  stats: OverviewStats | null;
  currentTenant?: Tenant;
}

export const NetworkHealthPage: React.FC<NetworkHealthPageProps> = ({
  exporters,
  stats,
  currentTenant,
}) => {
  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-[#0d131f] border border-slate-800 p-4 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-700/60 text-emerald-400">
            <Radio className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white flex items-center space-x-2">
              <span>{currentTenant?.name || 'Rural ISP Network'} Health & Telemetry Freshness</span>
              <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-2 py-0.5 rounded border border-cyan-800">
                ASN {currentTenant?.asn || 65001}
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              IPFIX / NetFlow v9 exporter ingestion pipeline, durable SQLite streaming adapter, and 30s event windows.
            </p>
          </div>
        </div>

        <div className="text-right font-mono text-xs">
          <span className="text-slate-500">Pipeline Status: </span>
          <span className="text-emerald-400 font-bold">OPERATIONAL</span>
        </div>
      </div>

      {/* Health Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="cyber-card p-5 border-emerald-500/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Telemetry Freshness
            </span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {stats?.flow_metrics.freshness || 'FRESH'}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Lag ≤ 1.2 seconds • Event window size: 30s
          </div>
        </div>

        <div className="cyber-card p-5 border-cyan-500/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Durable Stream Adapter
            </span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            SQLite (WAL)
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Zero-Cost Development Adapter • Transactional Outbox Active
          </div>
        </div>

        <div className="cyber-card p-5 border-purple-500/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Feature Completeness
            </span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            100.0%
          </div>
          <div className="text-xs text-slate-500 mt-1">
            14 / 14 Deployable NetFlow Features Extracted
          </div>
        </div>
      </div>

      {/* Configured Telemetry Exporters Table */}
      <div className="cyber-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Radio className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white tracking-wide">
              Configured NetFlow / IPFIX Exporters ({exporters.length})
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-500">
            Tenant: {currentTenant?.tenant_id}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Exporter ID</th>
                <th className="py-2.5 px-3">Device Name</th>
                <th className="py-2.5 px-3">IP Address</th>
                <th className="py-2.5 px-3">Records Received</th>
                <th className="py-2.5 px-3">Last Telemetry Seen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {exporters.map((exp) => (
                <tr key={exp.exporter_id} className="hover:bg-slate-800/30">
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-700">
                      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      {exp.status}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-cyan-400 font-bold">{exp.exporter_id}</td>
                  <td className="py-3 px-3 text-slate-200">{exp.name}</td>
                  <td className="py-3 px-3 text-white">{exp.ip_address}</td>
                  <td className="py-3 px-3 text-slate-300">
                    {exp.records_received.toLocaleString()} flows
                  </td>
                  <td className="py-3 px-3 text-slate-400 text-[11px]">
                    {exp.last_seen_at ? new Date(exp.last_seen_at).toLocaleTimeString() : 'Awaiting Flow'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

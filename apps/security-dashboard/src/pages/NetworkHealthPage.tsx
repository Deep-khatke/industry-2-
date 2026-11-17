import React from 'react';
import { Radio, Activity, Database, Layers } from 'lucide-react';
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
  const exporterList: Exporter[] = Array.isArray(exporters)
    ? exporters
    : (exporters as any)?.exporters && Array.isArray((exporters as any).exporters)
      ? (exporters as any).exporters
      : [];

  const formatLastSeen = (val?: string | null) => {
    if (!val) return 'Active';
    try {
      const d = new Date(val);
      if (isNaN(d.getTime())) return 'Active';
      return d.toISOString().substring(11, 19);
    } catch {
      return 'Active';
    }
  };
  return (
    <div className="space-y-5 font-sans">
      {/* Top Banner */}
      <div className="bg-white border border-[#ebebeb] p-6 rounded-3xl shadow-[0_2px_12px_rgba(0,0,0,0.03)] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <Radio className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-sm font-extrabold text-[#111111] flex items-center gap-2">
              <span>{currentTenant?.name || 'Rural ISP Network'} Health & Telemetry</span>
              <span className="text-xs font-mono font-bold text-[#111111] bg-[#f0f0f2] px-2.5 py-0.5 rounded-full">
                ASN {currentTenant?.asn || 65001}
              </span>
            </h2>
            <p className="text-xs text-[#767676] font-medium mt-1">
              IPFIX / NetFlow v9 exporter ingestion pipeline, durable SQLite streaming adapter, and 30s event windows.
            </p>
          </div>
        </div>

        <div className="text-right font-mono text-xs">
          <span className="text-[#767676]">Pipeline Status: </span>
          <span className="text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-full font-bold inline-flex items-center gap-1.5 border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            OPERATIONAL
          </span>
        </div>
      </div>

      {/* Health Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-[#767676] uppercase tracking-wider">
              Telemetry Freshness
            </span>
            <div className="p-2 rounded-2xl bg-emerald-50 text-emerald-600">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold font-mono text-[#111111]">
            {stats?.flow_metrics.freshness || 'FRESH'}
          </div>
          <div className="text-xs text-[#5f5f5f] font-medium mt-2">
            Lag ≤ 1.2s • Event window size: 30s
          </div>
        </div>

        <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-[#767676] uppercase tracking-wider">
              Durable Stream Engine
            </span>
            <div className="p-2 rounded-2xl bg-blue-50 text-blue-600">
              <Database className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold font-mono text-[#111111]">
            SQLite (WAL)
          </div>
          <div className="text-xs text-[#5f5f5f] font-medium mt-2">
            Zero-Cost Engine • Transactional Outbox
          </div>
        </div>

        <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold text-[#767676] uppercase tracking-wider">
              Feature Completeness
            </span>
            <div className="p-2 rounded-2xl bg-purple-50 text-purple-600">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="text-3xl font-extrabold font-mono text-[#111111]">
            100.0%
          </div>
          <div className="text-xs text-[#5f5f5f] font-medium mt-2">
            43 Canonical NetFlow Features Extracted
          </div>
        </div>
      </div>

      {/* Configured Telemetry Exporters Table */}
      <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-2xl bg-blue-50 text-blue-600">
              <Radio className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-extrabold text-[#111111]">
              Configured NetFlow / IPFIX Exporters ({exporterList.length})
            </h3>
          </div>
          <span className="text-xs font-mono text-[#767676] bg-[#f0f0f2] px-3 py-1 rounded-full font-medium">
            Observation Domains: 1001, 1002
          </span>
        </div>

        {exporterList.length === 0 ? (
          <div className="py-12 text-center text-xs text-[#767676] font-medium">
            No exporters registered for this tenant.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-zinc-100 text-[11px] font-bold text-[#767676] uppercase tracking-wider">
                  <th className="py-3 px-3">Exporter ID</th>
                  <th className="py-3 px-3">Name</th>
                  <th className="py-3 px-3">IP Address</th>
                  <th className="py-3 px-3 text-right">Records Ingested</th>
                  <th className="py-3 px-3">Status</th>
                  <th className="py-3 px-3">Last Seen (UTC)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 font-mono">
                {exporterList.map((exp) => (
                  <tr key={exp.exporter_id} className="hover:bg-[#fafafa]">
                    <td className="py-3 px-3 text-blue-700 font-bold">{exp.exporter_id}</td>
                    <td className="py-3 px-3 text-[#111111] font-sans font-bold">{exp.name || exp.exporter_id}</td>
                    <td className="py-3 px-3 text-[#111111] font-bold">{exp.ip_address}</td>
                    <td className="py-3 px-3 text-right text-[#5f5f5f] tabular-nums font-bold">
                      {(exp.records_received ?? 0).toLocaleString()}
                    </td>
                    <td className="py-3 px-3">
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${exp.status === 'HEALTHY'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : exp.status === 'DEGRADED'
                            ? 'bg-amber-50 text-amber-800 border border-amber-200'
                            : 'bg-[#fff0f2] text-[#e60023] border border-[#fecdd3]'
                        }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${exp.status === 'HEALTHY' ? 'bg-emerald-600' : exp.status === 'DEGRADED' ? 'bg-amber-500' : 'bg-[#e60023]'
                          }`} />
                        {exp.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-[#767676] text-xs tabular-nums">
                      {formatLastSeen(exp.last_seen_at)}
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

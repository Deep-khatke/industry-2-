import React, { useState } from 'react';
import { Flame, ShieldAlert, Cpu, Search, CheckCircle2, Zap } from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { Incident } from '../types/api';

interface ThreatMonitoringPageProps {
  incidents: Incident[];
  onSelectIncident: (incident: Incident) => void;
}

export const ThreatMonitoringPage: React.FC<ThreatMonitoringPageProps> = ({
  incidents,
  onSelectIncident,
}) => {
  const [filterCategory, setFilterCategory] = useState<string>('ALL');
  const [searchTarget, setSearchTarget] = useState<string>('');

  const filtered = incidents.filter((inc) => {
    if (filterCategory !== 'ALL' && inc.attack_category !== filterCategory) return false;
    if (searchTarget && !inc.target_ip.includes(searchTarget) && !inc.title.toLowerCase().includes(searchTarget.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-[#0d131f] border border-slate-800 p-4 rounded-xl">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-orange-950/60 border border-orange-700/60 text-orange-400">
            <Flame className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Live Threat Telemetry Feed</h2>
            <p className="text-xs text-slate-400">
              Aggregated 30-second event-time windows evaluated against verified LightGBM inference & deterministic rules.
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter by target IP..."
              value={searchTarget}
              onChange={(e) => setSearchTarget(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-48"
            />
          </div>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Categories</option>
            <option value="DDoS">DDoS / Flood</option>
            <option value="PortScan">PortScan</option>
            <option value="Reconnaissance">Reconnaissance</option>
            <option value="Suspicious Traffic">Suspicious Traffic</option>
          </select>
        </div>
      </div>

      {/* Threats Grid / Feed */}
      <div className="cyber-card p-5">
        <div className="flex items-center justify-between mb-4">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Detected Threat Events ({filtered.length})
          </span>
          <span className="text-xs font-mono text-cyan-400">
            Inference Target: p95 ≤ 5s • Measured CPU: 0.456ms
          </span>
        </div>

        {filtered.length === 0 ? (
          <div className="py-16 text-center text-slate-500 font-mono text-xs">
            No threat detections matching filter. Click "DDoS Burst" or "Port Scan" in the top bar to inject telemetry.
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((inc) => {
              let evidence: any = {};
              try {
                evidence = JSON.parse(inc.evidence_json);
              } catch {
                evidence = {};
              }

              return (
                <div
                  key={inc.incident_id}
                  onClick={() => onSelectIncident(inc)}
                  className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-cyan-500/50 transition-all cursor-pointer space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center space-x-3">
                      <StatusBadge type="severity" value={inc.severity} />
                      <span className="text-sm font-bold text-slate-200">{inc.title}</span>
                      <span className="text-xs font-mono text-slate-500">[{inc.incident_id}]</span>
                    </div>
                    <div className="flex items-center space-x-3">
                      <div className="text-xs font-mono text-slate-400">
                        Risk Score: <span className="text-cyan-400 font-bold">{(inc.risk_score * 100).toFixed(1)}%</span>
                      </div>
                      <StatusBadge type="incident_status" value={inc.status} />
                    </div>
                  </div>

                  {/* Flow Evidence Badges */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-800/60 text-[11px] font-mono">
                    <div className="bg-slate-950/60 p-2 rounded border border-slate-800/40">
                      <span className="text-slate-500 block text-[10px]">TARGET IP:PORT</span>
                      <span className="text-cyan-400 font-bold">
                        {inc.target_ip}:{inc.target_port}
                      </span>
                    </div>
                    <div className="bg-slate-950/60 p-2 rounded border border-slate-800/40">
                      <span className="text-slate-500 block text-[10px]">CATEGORY</span>
                      <span className="text-white">{inc.attack_category}</span>
                    </div>
                    <div className="bg-slate-950/60 p-2 rounded border border-slate-800/40">
                      <span className="text-slate-500 block text-[10px]">DETECTION LOGIC</span>
                      <span className="text-purple-400">
                        {evidence.matched_rules?.length ? evidence.matched_rules.join(', ') : 'LightGBM ML'}
                      </span>
                    </div>
                    <div className="bg-slate-950/60 p-2 rounded border border-slate-800/40">
                      <span className="text-slate-500 block text-[10px]">TIMESTAMP (UTC)</span>
                      <span className="text-slate-300">
                        {new Date(inc.created_at).toISOString().split('T')[1].replace('Z', '')}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

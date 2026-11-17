import React, { useState } from 'react';
import { Flame, ShieldAlert, Cpu, Search, CheckCircle2, Zap, ArrowRight } from 'lucide-react';
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
    <div className="space-y-5 font-sans">
      {/* Header bar */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white border border-[#ebebeb] p-5 rounded-3xl shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
            <Flame className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-extrabold text-[#111111]">Live Threat Stream</h2>
            <p className="text-xs text-[#767676] font-medium mt-0.5">
              Aggregated 30-second NetFlow windows evaluated against verified LightGBM inference & rules engine.
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <Search className="w-4 h-4 text-[#767676] absolute left-3.5 top-3" />
            <input
              type="text"
              placeholder="Filter by target IP..."
              value={searchTarget}
              onChange={(e) => setSearchTarget(e.target.value)}
              className="bg-[#f0f0f2] hover:bg-[#e9e9eb] focus:bg-white border border-transparent focus:border-[#e60023] rounded-full pl-10 pr-4 py-2 text-xs text-[#111111] placeholder-[#767676] font-medium focus:outline-none w-52 transition-colors"
            />
          </div>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="bg-[#f0f0f2] border-0 rounded-full px-4 py-2 text-xs font-bold text-[#111111] focus:outline-none focus:ring-2 focus:ring-[#e60023]/20 cursor-pointer"
          >
            <option value="ALL">All Categories</option>
            <option value="DDoS">DDoS / Volumetric Flood</option>
            <option value="PortScan">PortScan</option>
            <option value="Reconnaissance">Reconnaissance</option>
            <option value="Suspicious Traffic">Suspicious Traffic</option>
          </select>
        </div>
      </div>

      {/* Threats Grid / Feed */}
      <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
        <div className="flex items-center justify-between mb-4 pb-3 border-b border-zinc-100">
          <span className="text-xs font-bold text-[#111111] uppercase tracking-wider">
            Detected Threat Events ({filtered.length})
          </span>
          <span className="text-xs font-mono text-[#767676] bg-[#f0f0f2] px-3 py-1 rounded-full font-medium">
            Inference Target: &lt; 25ms • Measured CPU: 9.68ms
          </span>
        </div>

        {filtered.length === 0 ? (
          <div className="py-16 text-center text-[#767676] font-medium text-xs">
            No threat detections matching filter. Use "Simulate Telemetry" in the top bar to inject attack flows.
          </div>
        ) : (
          <div className="space-y-3.5">
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
                  className="p-5 rounded-2xl bg-white border border-zinc-200/80 hover:border-[#e60023] shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer space-y-3 group"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <StatusBadge type="severity" value={inc.severity} />
                      <span className="text-sm font-bold text-[#111111] group-hover:text-[#e60023] transition-colors">{inc.title}</span>
                      <span className="text-xs font-mono text-[#767676]">[{inc.incident_id}]</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-xs font-mono text-[#767676]">
                        Risk: <span className="text-[#111111] font-bold">{(inc.risk_score * 100).toFixed(1)}%</span>
                      </div>
                      <StatusBadge type="incident_status" value={inc.status} />
                    </div>
                  </div>

                  {/* Flow Evidence Badges */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-3 border-t border-zinc-100 text-xs font-mono">
                    <div className="bg-[#fafafa] p-2.5 rounded-2xl border border-zinc-100">
                      <span className="text-[#767676] block text-[10px] uppercase font-bold">TARGET IP:PORT</span>
                      <span className="text-[#e60023] font-bold">
                        {inc.target_ip}:{inc.target_port}
                      </span>
                    </div>
                    <div className="bg-[#fafafa] p-2.5 rounded-2xl border border-zinc-100">
                      <span className="text-[#767676] block text-[10px] uppercase font-bold">ATTACK CATEGORY</span>
                      <span className="text-[#111111] font-bold">{inc.attack_category}</span>
                    </div>
                    <div className="bg-[#fafafa] p-2.5 rounded-2xl border border-zinc-100">
                      <span className="text-[#767676] block text-[10px] uppercase font-bold">DETECTION LOGIC</span>
                      <span className="text-amber-700 font-bold">
                        {evidence.matched_rules?.length ? evidence.matched_rules.join(', ') : 'LightGBM Ensemble'}
                      </span>
                    </div>
                    <div className="bg-[#fafafa] p-2.5 rounded-2xl border border-zinc-100">
                      <span className="text-[#767676] block text-[10px] uppercase font-bold">DETECTED (UTC)</span>
                      <span className="text-[#111111]">
                        {new Date(inc.created_at).toISOString().substring(11, 19)}
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

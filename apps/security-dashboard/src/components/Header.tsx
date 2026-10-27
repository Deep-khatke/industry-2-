import React, { useEffect, useState } from 'react';
import { RefreshCw, Shield, Play, RotateCcw, AlertOctagon, CheckCircle2 } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
  onRefresh: () => void;
  isRefreshing: boolean;
  refreshInterval: number;
  onRefreshIntervalChange: (interval: number) => void;
  onTriggerReplay: (scenario: 'normal' | 'suspicious' | 'scanning') => void;
  onResetDb: () => void;
  isReplaying: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  onRefresh,
  isRefreshing,
  refreshInterval,
  onRefreshIntervalChange,
  onTriggerReplay,
  onResetDb,
  isReplaying,
}) => {
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().replace('GMT', 'UTC'));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 bg-[#0a0f1d]/90 backdrop-blur-md border-b border-slate-800/80 px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Title & Subtitle */}
      <div>
        <h1 className="text-base font-bold text-white tracking-wide flex items-center space-x-2">
          <span>{title}</span>
        </h1>
        {subtitle && <p className="text-[11px] text-slate-400 font-medium">{subtitle}</p>}
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-4">
        {/* UTC Clock */}
        <div className="hidden lg:flex items-center space-x-2 px-3 py-1 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>{utcTime}</span>
        </div>

        {/* Response Mode Badge */}
        <div className="flex items-center space-x-1.5 px-3 py-1 rounded-lg bg-emerald-950/60 border border-emerald-700/60 text-emerald-400 text-xs font-semibold shadow-[0_0_10px_rgba(16,185,129,0.15)]">
          <Shield className="w-3.5 h-3.5 text-emerald-400" />
          <span>MANUAL MODE</span>
          <span
            className="ml-1 text-[10px] text-slate-400 bg-slate-900/90 px-1.5 py-0.5 rounded border border-slate-800 cursor-help"
            title="AUTO response is unavailable until dedicated safety qualification phase."
          >
            AUTO: OFF
          </span>
        </div>

        {/* Replay Controls Group */}
        <div className="flex items-center space-x-1.5 bg-slate-900/90 border border-slate-800 p-1 rounded-lg">
          <span className="text-[10px] uppercase font-bold text-slate-500 px-2 font-mono">REPLAY:</span>
          <button
            onClick={() => onTriggerReplay('normal')}
            disabled={isReplaying}
            className="px-2 py-1 text-[11px] font-semibold rounded bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors disabled:opacity-50"
            title="Simulate normal benign flows"
          >
            Normal
          </button>
          <button
            onClick={() => onTriggerReplay('suspicious')}
            disabled={isReplaying}
            className="px-2 py-1 text-[11px] font-semibold rounded bg-red-950/80 text-red-300 border border-red-800/60 hover:bg-red-900 transition-colors disabled:opacity-50"
            title="Simulate volumetric DDoS flood"
          >
            DDoS Burst
          </button>
          <button
            onClick={() => onTriggerReplay('scanning')}
            disabled={isReplaying}
            className="px-2 py-1 text-[11px] font-semibold rounded bg-amber-950/80 text-amber-300 border border-amber-800/60 hover:bg-amber-900 transition-colors disabled:opacity-50"
            title="Simulate SYN port scan probe"
          >
            Port Scan
          </button>
          <button
            onClick={onResetDb}
            disabled={isReplaying}
            className="p-1 text-slate-400 hover:text-red-400 rounded hover:bg-slate-800 transition-colors"
            title="Reset demonstration database"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Refresh & Polling */}
        <div className="flex items-center space-x-2">
          <select
            value={refreshInterval}
            onChange={(e) => onRefreshIntervalChange(Number(e.target.value))}
            className="bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-300 px-2 py-1 focus:outline-none focus:border-cyan-500"
          >
            <option value={0}>Poll: Off</option>
            <option value={3000}>Poll: 3s</option>
            <option value={5000}>Poll: 5s</option>
            <option value={10000}>Poll: 10s</option>
          </select>
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-2 bg-slate-900 border border-slate-800 rounded-lg text-slate-300 hover:text-cyan-400 hover:border-cyan-500/50 transition-all disabled:opacity-50"
            title="Refresh dashboard data now"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};

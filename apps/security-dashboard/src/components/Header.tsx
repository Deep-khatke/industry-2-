import React, { useEffect, useState } from 'react';
import { RefreshCw, Shield, Play, RotateCcw, ChevronDown, Sparkles } from 'lucide-react';

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
  const [showReplayMenu, setShowReplayMenu] = useState<boolean>(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(
        now.toISOString().substring(11, 19) + ' UTC'
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 bg-white/95 backdrop-blur border-b border-[#ebebeb] px-6 flex items-center justify-between sticky top-0 z-20 font-sans shadow-[0_1px_6px_rgba(0,0,0,0.02)]">
      {/* Title & Section Context */}
      <div className="flex items-center gap-3">
        <div>
          <h1 className="text-base font-extrabold text-[#111111] tracking-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="text-xs text-[#767676] font-medium leading-none mt-0.5 truncate max-w-xl">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* UTC Clock */}
        <div className="hidden xl:flex items-center gap-1.5 px-3 py-1.5 bg-[#f0f0f2] rounded-full text-xs font-mono font-medium text-[#111111] tabular-nums">
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <span>{utcTime}</span>
        </div>

        {/* Response Mode Safety Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold">
          <Shield className="w-3.5 h-3.5 text-emerald-600" />
          <span>Manual Mode</span>
          <span
            className="text-[10px] text-zinc-500 bg-white px-2 py-0.5 rounded-full border border-emerald-200 ml-1 font-mono font-semibold"
            title="Gate G13 (Autonomous Direct Router Mitigation) is strictly BLOCKED."
          >
            G13 BLOCKED
          </span>
        </div>

        {/* Telemetry Replay Control */}
        <div className="relative">
          <button
            onClick={() => setShowReplayMenu(!showReplayMenu)}
            disabled={isReplaying}
            className="flex items-center gap-2 px-4 py-2 rounded-full bg-[#e60023] hover:bg-[#bd081c] text-white text-xs font-bold transition-all shadow-sm disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{isReplaying ? 'Replaying...' : 'Simulate Telemetry'}</span>
            <ChevronDown className="w-3.5 h-3.5" />
          </button>

          {showReplayMenu && (
            <div className="absolute right-0 mt-2 w-64 bg-white border border-[#ebebeb] rounded-2xl shadow-xl z-50 p-2 space-y-1">
              <div className="px-3 py-1 text-[10px] font-bold text-[#767676] uppercase tracking-wider">
                Select Attack Scenario
              </div>
              <button
                onClick={() => {
                  onTriggerReplay('suspicious');
                  setShowReplayMenu(false);
                }}
                className="w-full text-left px-3 py-2 rounded-xl text-xs hover:bg-[#fff0f2] text-[#111111] flex items-center justify-between transition-colors"
              >
                <div>
                  <div className="font-bold text-[#e60023]">Volumetric DDoS Flood</div>
                  <div className="text-[10px] text-[#767676]">Generates CRITICAL incident</div>
                </div>
                <Play className="w-3.5 h-3.5 text-[#e60023]" />
              </button>

              <button
                onClick={() => {
                  onTriggerReplay('scanning');
                  setShowReplayMenu(false);
                }}
                className="w-full text-left px-3 py-2 rounded-xl text-xs hover:bg-orange-50 text-[#111111] flex items-center justify-between transition-colors"
              >
                <div>
                  <div className="font-bold text-orange-600">Horizontal Port Sweep</div>
                  <div className="text-[10px] text-[#767676]">Generates MEDIUM incident</div>
                </div>
                <Play className="w-3.5 h-3.5 text-orange-600" />
              </button>

              <button
                onClick={() => {
                  onTriggerReplay('normal');
                  setShowReplayMenu(false);
                }}
                className="w-full text-left px-3 py-2 rounded-xl text-xs hover:bg-emerald-50 text-[#111111] flex items-center justify-between transition-colors"
              >
                <div>
                  <div className="font-bold text-emerald-700">Benign Traffic Baseline</div>
                  <div className="text-[10px] text-[#767676]">0 false positive alarms</div>
                </div>
                <Play className="w-3.5 h-3.5 text-emerald-600" />
              </button>
            </div>
          )}
        </div>

        {/* Polling Interval Selector */}
        <select
          value={refreshInterval}
          onChange={(e) => onRefreshIntervalChange(Number(e.target.value))}
          className="bg-[#f0f0f2] border-0 text-[#111111] text-xs font-semibold rounded-full px-3 py-2 cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#e60023]/20"
          title="Polling Interval"
        >
          <option value={3000}>3s live</option>
          <option value={5000}>5s default</option>
          <option value={10000}>10s slow</option>
          <option value={0}>Manual only</option>
        </select>

        {/* Manual Refresh */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="p-2 rounded-full bg-[#f0f0f2] hover:bg-[#e2e2e4] text-[#111111] transition-colors"
          title="Refresh Data Now"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-[#e60023]' : ''}`} />
        </button>

        {/* Reset Database */}
        <button
          onClick={onResetDb}
          className="p-2 rounded-full bg-[#f0f0f2] hover:bg-[#fff0f2] hover:text-[#e60023] text-[#767676] transition-colors"
          title="Reset Demo Database"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};

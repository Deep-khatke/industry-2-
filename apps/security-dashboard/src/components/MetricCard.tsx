import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  badge?: React.ReactNode;
  variant?: 'cyan' | 'red' | 'amber' | 'emerald' | 'purple' | 'default';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  badge,
  variant = 'default',
}) => {
  const borderVariants = {
    cyan: 'border-cyan-500/30 hover:border-cyan-400/50',
    red: 'border-red-500/30 hover:border-red-400/50',
    amber: 'border-amber-500/30 hover:border-amber-400/50',
    emerald: 'border-emerald-500/30 hover:border-emerald-400/50',
    purple: 'border-purple-500/30 hover:border-purple-400/50',
    default: 'border-slate-800 hover:border-slate-700',
  };

  const iconBgVariants = {
    cyan: 'bg-cyan-950/60 text-cyan-400 border border-cyan-700/40',
    red: 'bg-red-950/60 text-red-400 border border-red-700/40',
    amber: 'bg-amber-950/60 text-amber-400 border border-amber-700/40',
    emerald: 'bg-emerald-950/60 text-emerald-400 border border-emerald-700/40',
    purple: 'bg-purple-950/60 text-purple-400 border border-purple-700/40',
    default: 'bg-slate-800 text-slate-300 border border-slate-700',
  };

  return (
    <div className={`cyber-card p-5 ${borderVariants[variant]}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-400 tracking-wider uppercase">
          {title}
        </span>
        <div className={`p-2 rounded-lg ${iconBgVariants[variant]}`}>
          {icon}
        </div>
      </div>
      <div className="flex items-baseline justify-between">
        <div className="text-2xl font-bold text-white font-mono tracking-tight">
          {value}
        </div>
        {badge && <div>{badge}</div>}
      </div>
      {subtitle && (
        <div className="mt-2 text-xs text-slate-500 font-medium truncate">
          {subtitle}
        </div>
      )}
    </div>
  );
};

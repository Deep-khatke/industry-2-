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
  const iconBg = {
    cyan: 'bg-blue-50 text-blue-600 border-blue-100',
    red: 'bg-[#fff0f2] text-[#e60023] border-[#fecdd3]',
    amber: 'bg-amber-50 text-amber-600 border-amber-100',
    emerald: 'bg-emerald-50 text-emerald-600 border-emerald-100',
    purple: 'bg-purple-50 text-purple-600 border-purple-100',
    default: 'bg-zinc-100 text-zinc-700 border-zinc-200',
  };

  return (
    <div className="bg-white rounded-3xl p-5 border border-zinc-200/80 shadow-[0_2px_12px_rgba(0,0,0,0.03)] hover:shadow-[0_8px_24px_rgba(0,0,0,0.08)] hover:-translate-y-1 transition-all duration-200">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-bold text-[#767676] uppercase tracking-wider">
          {title}
        </span>
        <div className={`p-2 rounded-2xl border ${iconBg[variant]}`}>
          {icon}
        </div>
      </div>
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-3xl font-extrabold text-[#111111] font-mono tracking-tight tabular-nums truncate">
          {value}
        </div>
        {badge && <div className="shrink-0">{badge}</div>}
      </div>
      {subtitle && (
        <div className="mt-3 pt-2.5 border-t border-zinc-100 text-xs text-[#5f5f5f] font-medium truncate flex items-center justify-between">
          <span>{subtitle}</span>
        </div>
      )}
    </div>
  );
};

import React from 'react';
import { Severity, IncidentStatus, ActionStatus } from '../types/api';

interface StatusBadgeProps {
  type: 'severity' | 'incident_status' | 'action_status';
  value: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, value }) => {
  if (type === 'severity') {
    const sev = value as Severity;
    switch (sev) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950/80 text-red-400 border border-red-700/60 shadow-[0_0_8px_rgba(239,68,68,0.3)]">
            <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-red-500 animate-pulse" />
            CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-950/80 text-orange-400 border border-orange-700/60">
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-400 border border-amber-700/60">
            MEDIUM
          </span>
        );
      case 'LOW':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950/80 text-blue-400 border border-blue-700/60">
            LOW
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            {value}
          </span>
        );
    }
  }

  if (type === 'incident_status') {
    const status = value as IncidentStatus;
    switch (status) {
      case 'NEW':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950/80 text-cyan-300 border border-cyan-600/60">
            <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-cyan-400 animate-ping" />
            NEW
          </span>
        );
      case 'ACKNOWLEDGED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-950/80 text-indigo-300 border border-indigo-700">
            ACKNOWLEDGED
          </span>
        );
      case 'INVESTIGATING':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-950/80 text-purple-300 border border-purple-700">
            INVESTIGATING
          </span>
        );
      case 'ACTION_PENDING':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-300 border border-amber-700">
            ACTION PENDING
          </span>
        );
      case 'MITIGATED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-600/80 shadow-[0_0_8px_rgba(16,185,129,0.3)]">
            MITIGATED
          </span>
        );
      case 'RESOLVED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-green-950/80 text-green-300 border border-green-700">
            RESOLVED
          </span>
        );
      case 'FALSE_POSITIVE':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700 line-through">
            FALSE POSITIVE
          </span>
        );
      case 'CLOSED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-900 text-slate-500 border border-slate-800">
            CLOSED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400">
            {value}
          </span>
        );
    }
  }

  if (type === 'action_status') {
    const act = value as ActionStatus;
    switch (act) {
      case 'VERIFIED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-600 shadow-[0_0_8px_rgba(16,185,129,0.25)]">
            VERIFIED ACTIVE
          </span>
        );
      case 'PENDING':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950/80 text-amber-400 border border-amber-600">
            PENDING
          </span>
        );
      case 'ROLLED_BACK':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-600">
            ROLLED BACK
          </span>
        );
      case 'EXPIRED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-900 text-gray-500 border border-gray-700">
            EXPIRED
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-950 text-red-400 border border-red-700">
            FAILED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400">
            {value}
          </span>
        );
    }
  }

  return <span>{value}</span>;
};

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
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[#fff0f2] text-[#e60023] border border-[#fecdd3] shadow-sm">
            <span className="w-2 h-2 rounded-full bg-[#e60023]" />
            CRITICAL
          </span>
        );
      case 'HIGH':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-orange-50 text-orange-800 border border-orange-200">
            <span className="w-2 h-2 rounded-full bg-orange-500" />
            MEDIUM
          </span>
        );
      case 'LOW':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            LOW
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 text-zinc-700 border border-zinc-200">
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
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[#fff0f2] text-[#e60023] border border-[#fecdd3]">
            <span className="w-2 h-2 rounded-full bg-[#e60023]" />
            NEW
          </span>
        );
      case 'ACKNOWLEDGED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            ACKNOWLEDGED
          </span>
        );
      case 'INVESTIGATING':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
            <span className="w-2 h-2 rounded-full bg-purple-500" />
            INVESTIGATING
          </span>
        );
      case 'ACTION_PENDING':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            ACTION PENDING
          </span>
        );
      case 'MITIGATED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            MITIGATED
          </span>
        );
      case 'RESOLVED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 text-zinc-700 border border-zinc-200">
            <span className="w-2 h-2 rounded-full bg-zinc-400" />
            RESOLVED
          </span>
        );
      case 'FALSE_POSITIVE':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 text-zinc-500 border border-zinc-200 line-through">
            FALSE POSITIVE
          </span>
        );
      case 'CLOSED':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 text-zinc-500 border border-zinc-200">
            CLOSED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 text-zinc-600">
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
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-600" />
            SIMULATED ACTIVE
          </span>
        );
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            PENDING
          </span>
        );
      case 'ROLLED_BACK':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 text-zinc-600 border border-zinc-200">
            ROLLED BACK
          </span>
        );
      case 'EXPIRED':
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 text-zinc-500 border border-zinc-200">
            EXPIRED
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#fff0f2] text-[#e60023] border border-[#fecdd3]">
            <span className="w-2 h-2 rounded-full bg-[#e60023]" />
            FAILED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-zinc-100 text-zinc-600">
            {value}
          </span>
        );
    }
  }

  return <span>{value}</span>;
};

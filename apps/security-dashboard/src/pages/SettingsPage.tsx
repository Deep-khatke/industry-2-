import React from 'react';
import { Settings, Shield, User, Lock, AlertOctagon, CheckCircle2, Server } from 'lucide-react';
import { ResponsePolicy, Tenant, User as UserType } from '../types/api';

interface SettingsPageProps {
  currentTenant?: Tenant;
  currentUser: UserType | null;
  policy: ResponsePolicy | null;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  currentTenant,
  currentUser,
  policy,
}) => {
  const rbacMatrix = [
    { role: 'TENANT_ADMIN', view: true, investigate: true, approve: true, manage: true },
    { role: 'SECURITY_RESPONDER', view: true, investigate: true, approve: true, manage: false },
    { role: 'SECURITY_ANALYST', view: true, investigate: true, approve: false, manage: false },
    { role: 'READ_ONLY', view: true, investigate: false, approve: false, manage: false },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-[#0d131f] border border-slate-800 p-4 rounded-xl flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-300">
            <Settings className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">System Settings & Response Policy</h2>
            <p className="text-xs text-slate-400">
              Tenant boundaries, role permissions, protected infrastructure allowlists, and safety constraints.
            </p>
          </div>
        </div>
      </div>

      {/* AUTO Mode Disabled Safety Warning Banner */}
      <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-600/60 flex items-start space-x-3 text-xs">
        <AlertOctagon className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold text-amber-300 uppercase tracking-wide">
            Automated Execution Disabled (Architecture Invariant)
          </div>
          <div className="text-slate-300 leading-relaxed">
            {policy?.auto_response_status ||
              'AUTO response is unavailable until the dedicated safety qualification phase.'}
          </div>
          <div className="text-[11px] text-amber-400/80 font-mono">
            Phase 4 strictly enforces MANUAL Mode with verified human administrator approval.
          </div>
        </div>
      </div>

      {/* Tenant Profile & Current User */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="cyber-card p-5 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center space-x-2">
            <Server className="w-4 h-4 text-cyan-400" />
            <span>Monitored Tenant Profile</span>
          </h3>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Tenant Identifier:</span>
              <span className="text-cyan-400 font-bold">{currentTenant?.tenant_id}</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">ISP Legal Name:</span>
              <span className="text-white">{currentTenant?.name}</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Autonomous System (ASN):</span>
              <span className="text-purple-400 font-bold">{currentTenant?.asn}</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Operating Region:</span>
              <span className="text-slate-300">{currentTenant?.region}</span>
            </div>
          </div>
        </div>

        <div className="cyber-card p-5 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center space-x-2">
            <User className="w-4 h-4 text-emerald-400" />
            <span>Current Authenticated Identity</span>
          </h3>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">User ID:</span>
              <span className="text-slate-300">{currentUser?.user_id}</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Username:</span>
              <span className="text-cyan-400 font-bold">{currentUser?.username}</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Full Name:</span>
              <span className="text-white">{currentUser?.full_name}</span>
            </div>
            <div className="flex justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Assigned Role:</span>
              <span className="text-emerald-400 font-bold">{currentUser?.role}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Role-Based Access Control (RBAC) Permissions Matrix */}
      <div className="cyber-card p-5">
        <h3 className="text-sm font-bold text-white mb-3 flex items-center space-x-2">
          <Shield className="w-4 h-4 text-purple-400" />
          <span>Role-Based Access Control (RBAC) Permissions Matrix</span>
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                <th className="py-2 px-3">Role</th>
                <th className="py-2 px-3 text-center">View Telemetry & Incidents</th>
                <th className="py-2 px-3 text-center">Investigate Incidents</th>
                <th className="py-2 px-3 text-center">Approve Defensive Actions</th>
                <th className="py-2 px-3 text-center">Manage Tenant Settings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {rbacMatrix.map((r) => {
                const isCurrent = currentUser?.role === r.role;
                return (
                  <tr key={r.role} className={isCurrent ? 'bg-cyan-950/30 font-bold' : ''}>
                    <td className="py-2.5 px-3 text-slate-200">
                      {r.role} {isCurrent && <span className="text-cyan-400 text-[10px] ml-1">(YOU)</span>}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <span className="text-emerald-400">✓</span>
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {r.investigate ? <span className="text-emerald-400">✓</span> : <span className="text-slate-600">—</span>}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {r.approve ? <span className="text-emerald-400">✓</span> : <span className="text-slate-600">—</span>}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      {r.manage ? <span className="text-emerald-400">✓</span> : <span className="text-slate-600">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Protected Target Allowlist */}
      <div className="cyber-card p-5">
        <h3 className="text-sm font-bold text-white mb-2 flex items-center space-x-2">
          <Lock className="w-4 h-4 text-red-400" />
          <span>Protected Infrastructure (Strict Modification Ban)</span>
        </h3>
        <p className="text-xs text-slate-400 mb-3">
          The following loopback, default gateway, broadcast, and core ISP infrastructure subnets are protected by safety policy and cannot be targeted by temporary block or rate-limit actions:
        </p>
        <div className="flex flex-wrap gap-2 text-xs font-mono">
          {(policy?.protected_ip_ranges || [
            '127.0.0.1',
            '::1',
            '10.0.0.1',
            '192.168.1.1',
            '0.0.0.0/0',
            '255.255.255.255',
          ]).map((ip) => (
            <span
              key={ip}
              className="px-2.5 py-1 rounded bg-red-950/60 border border-red-700/60 text-red-400 font-bold"
            >
              {ip}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

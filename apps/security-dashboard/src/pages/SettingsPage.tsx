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
    <div className="space-y-6 font-sans">
      {/* Top Banner */}
      <div className="bg-white border border-[#ebebeb] p-6 rounded-3xl shadow-[0_2px_12px_rgba(0,0,0,0.03)] flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-zinc-100 text-zinc-700 flex items-center justify-center shrink-0">
            <Settings className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-base font-extrabold text-[#111111]">System Settings & Policy Matrix</h2>
            <p className="text-xs text-[#767676] font-medium mt-0.5">
              Tenant boundaries, role permissions, protected infrastructure allowlists, and safety constraints.
            </p>
          </div>
        </div>
      </div>

      {/* AUTO Mode Disabled Safety Warning Banner */}
      <div className="p-5 rounded-3xl bg-amber-50 border border-amber-200 flex items-start gap-3.5 text-xs">
        <AlertOctagon className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-extrabold text-amber-900 uppercase tracking-wide">
            Automated Direct Router Mitigation Blocked (Gate G13 Invariant)
          </div>
          <div className="text-amber-800 font-medium leading-relaxed">
            {policy?.auto_response_status ||
              'AUTO response is strictly unavailable until physical ISP router hardware qualification.'}
          </div>
          <div className="text-[11px] text-amber-700 font-mono font-bold">
            MANUAL Mode is strictly enforced with verified human administrator approval.
          </div>
        </div>
      </div>

      {/* Tenant Profile & Current User */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)] space-y-4">
          <h3 className="text-sm font-extrabold text-[#111111] flex items-center gap-2.5">
            <div className="p-2 rounded-2xl bg-blue-50 text-blue-600">
              <Server className="w-4 h-4" />
            </div>
            <span>Monitored Tenant Profile</span>
          </h3>
          <div className="space-y-2.5 text-xs font-mono">
            <div className="flex justify-between p-3 rounded-2xl bg-[#fafafa] border border-zinc-100">
              <span className="text-[#767676]">Tenant Identifier:</span>
              <span className="text-blue-700 font-bold">{currentTenant?.tenant_id}</span>
            </div>
            <div className="flex justify-between p-3 rounded-2xl bg-[#fafafa] border border-zinc-100">
              <span className="text-[#767676]">ISP Legal Name:</span>
              <span className="text-[#111111] font-bold">{currentTenant?.name}</span>
            </div>
            <div className="flex justify-between p-3 rounded-2xl bg-[#fafafa] border border-zinc-100">
              <span className="text-[#767676]">Autonomous System (ASN):</span>
              <span className="text-purple-700 font-bold">{currentTenant?.asn}</span>
            </div>
            <div className="flex justify-between p-3 rounded-2xl bg-[#fafafa] border border-zinc-100">
              <span className="text-[#767676]">Operating Region:</span>
              <span className="text-[#111111]">{currentTenant?.region}</span>
            </div>
          </div>
        </div>

        <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)] space-y-4">
          <h3 className="text-sm font-extrabold text-[#111111] flex items-center gap-2.5">
            <div className="p-2 rounded-2xl bg-emerald-50 text-emerald-600">
              <User className="w-4 h-4" />
            </div>
            <span>Current Authenticated Identity</span>
          </h3>
          <div className="space-y-2.5 text-xs font-mono">
            <div className="flex justify-between p-3 rounded-2xl bg-[#fafafa] border border-zinc-100">
              <span className="text-[#767676]">User ID:</span>
              <span className="text-[#5f5f5f]">{currentUser?.user_id}</span>
            </div>
            <div className="flex justify-between p-3 rounded-2xl bg-[#fafafa] border border-zinc-100">
              <span className="text-[#767676]">Username:</span>
              <span className="text-blue-700 font-bold">{currentUser?.username}</span>
            </div>
            <div className="flex justify-between p-3 rounded-2xl bg-[#fafafa] border border-zinc-100">
              <span className="text-[#767676]">Full Name:</span>
              <span className="text-[#111111] font-bold">{currentUser?.full_name}</span>
            </div>
            <div className="flex justify-between p-3 rounded-2xl bg-[#fafafa] border border-zinc-100">
              <span className="text-[#767676]">Assigned Role:</span>
              <span className="text-emerald-700 font-bold">{currentUser?.role}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Role-Based Access Control (RBAC) Permissions Matrix */}
      <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
        <h3 className="text-sm font-extrabold text-[#111111] mb-4 flex items-center gap-2.5">
          <div className="p-2 rounded-2xl bg-purple-50 text-purple-600">
            <Shield className="w-4 h-4" />
          </div>
          <span>Role-Based Access Control (RBAC) Permissions Matrix</span>
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-zinc-100 text-[11px] font-bold text-[#767676] uppercase tracking-wider">
                <th className="py-3 px-3">Role</th>
                <th className="py-3 px-3 text-center">View Telemetry & Incidents</th>
                <th className="py-3 px-3 text-center">Investigate Incidents</th>
                <th className="py-3 px-3 text-center">Approve Defensive Actions</th>
                <th className="py-3 px-3 text-center">Manage Tenant Settings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 font-mono">
              {rbacMatrix.map((r) => {
                const isCurrent = currentUser?.role === r.role;
                return (
                  <tr key={r.role} className={isCurrent ? 'bg-[#fff0f2] font-bold' : 'hover:bg-[#fafafa]'}>
                    <td className="py-3 px-3 text-[#111111]">
                      {r.role} {isCurrent && <span className="text-[#e60023] text-[10px] ml-1.5 font-bold">(YOU)</span>}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className="text-emerald-700 font-bold">✓</span>
                    </td>
                    <td className="py-3 px-3 text-center">
                      {r.investigate ? <span className="text-emerald-700 font-bold">✓</span> : <span className="text-[#767676]">—</span>}
                    </td>
                    <td className="py-3 px-3 text-center">
                      {r.approve ? <span className="text-emerald-700 font-bold">✓</span> : <span className="text-[#767676]">—</span>}
                    </td>
                    <td className="py-3 px-3 text-center">
                      {r.manage ? <span className="text-emerald-700 font-bold">✓</span> : <span className="text-[#767676]">—</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Protected Target Allowlist */}
      <div className="bg-white border border-[#ebebeb] rounded-3xl p-6 shadow-[0_2px_12px_rgba(0,0,0,0.03)]">
        <h3 className="text-sm font-extrabold text-[#111111] mb-2 flex items-center gap-2.5">
          <div className="p-2 rounded-2xl bg-[#fff0f2] text-[#e60023]">
            <Lock className="w-4 h-4" />
          </div>
          <span>Protected Infrastructure (Strict Modification Ban)</span>
        </h3>
        <p className="text-xs text-[#767676] font-medium mb-4">
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
              className="px-3.5 py-1.5 rounded-full bg-[#fff0f2] border border-[#fecdd3] text-[#e60023] font-bold"
            >
              {ip}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

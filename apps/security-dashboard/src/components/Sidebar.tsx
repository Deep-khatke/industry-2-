import React from 'react';
import {
  Shield,
  Activity,
  AlertTriangle,
  Radio,
  Cpu,
  Settings,
  Share2,
  ChevronDown,
  User,
  LogOut,
  Building2,
  Eye,
  CheckCircle2,
} from 'lucide-react';
import { Tenant, User as UserType } from '../types/api';

interface SidebarProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  tenants: Tenant[];
  selectedTenantId: string;
  onTenantChange: (tenantId: string) => void;
  currentUser: UserType | null;
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onTabChange,
  tenants,
  selectedTenantId,
  onTenantChange,
  currentUser,
  onLogout,
}) => {
  const navSections = [
    {
      title: 'Operations',
      items: [
        { id: 'overview', label: 'Overview', icon: Activity },
        { id: 'incidents', label: 'Incidents', icon: AlertTriangle },
        { id: 'actions', label: 'Response Center', icon: Shield },
      ],
    },
    {
      title: 'Infrastructure & AI',
      items: [
        { id: 'pilot', label: 'Pilot Operations', icon: Eye },
        { id: 'health', label: 'Network Exporters', icon: Radio },
        { id: 'models', label: 'Model Governance', icon: Cpu },
      ],
    },
    {
      title: 'Consortium & Trust',
      items: [
        { id: 'federation', label: 'Federated Learning', icon: Share2 },
        { id: 'governance', label: 'Ledger Audit', icon: Building2 },
        { id: 'settings', label: 'Settings & Policy', icon: Settings },
      ],
    },
  ];

  const currentTenant = tenants.find((t) => t.tenant_id === selectedTenantId);

  return (
    <aside className="w-64 bg-white border-r border-[#ebebeb] shadow-[2px_0_12px_rgba(0,0,0,0.02)] flex flex-col h-screen fixed left-0 top-0 select-none z-30 font-sans">
      {/* Brand Header */}
      <div className="p-4 border-b border-[#ebebeb] flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl bg-[#e60023] flex items-center justify-center text-white shadow-sm shrink-0">
          <Shield className="w-5 h-5 fill-white/20" />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-bold tracking-tight text-[#111111] truncate">
            Cyber Shield
          </div>
          <div className="text-[11px] text-[#767676] font-medium tracking-wide truncate">
            Consortium Security SOC
          </div>
        </div>
      </div>

      {/* Tenant Switcher */}
      <div className="p-3 border-b border-[#ebebeb] bg-[#fafafa]">
        <div className="text-[10px] font-bold text-[#767676] uppercase tracking-wider mb-1.5 flex items-center justify-between px-1">
          <span>Active ISP Workspace</span>
          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded-full border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            LIVE
          </span>
        </div>
        <div className="relative">
          <select
            value={selectedTenantId}
            onChange={(e) => onTenantChange(e.target.value)}
            className="w-full bg-white border border-[#ebebeb] text-[#111111] text-xs font-semibold rounded-2xl px-3 py-2 appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#e60023]/20 shadow-sm"
          >
            {tenants.map((t) => (
              <option key={t.tenant_id} value={t.tenant_id}>
                {t.name} (ASN {t.asn})
              </option>
            ))}
          </select>
          <ChevronDown className="w-4 h-4 text-[#767676] absolute right-3 top-2.5 pointer-events-none" />
        </div>
        {currentTenant && (
          <div className="mt-2 text-[10px] text-[#767676] font-medium flex items-center justify-between px-1">
            <span>Region: {currentTenant.region}</span>
            <span className="font-mono text-[#111111]">ASN {currentTenant.asn}</span>
          </div>
        )}
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-4">
        {navSections.map((section) => (
          <div key={section.title} className="space-y-1">
            <div className="text-[10px] font-bold uppercase tracking-wider text-[#767676] px-3.5 py-1">
              {section.title}
            </div>
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = currentTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onTabChange(item.id)}
                    className={`w-full flex items-center gap-3 px-3.5 py-2 rounded-full text-xs font-bold transition-all ${
                      isActive
                        ? 'bg-[#111111] text-white shadow-sm'
                        : 'text-[#5f5f5f] hover:text-[#111111] hover:bg-[#f0f0f2]'
                    }`}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-[#767676]'}`} />
                    <span className="truncate">{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Zero Cost Assurance Pill */}
      <div className="px-3 py-2 border-t border-[#ebebeb] bg-[#fafafa]">
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-bold">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
          <span className="truncate">Zero-Cost Policy Verified</span>
        </div>
      </div>

      {/* User Session Footer */}
      <div className="p-3 border-t border-[#ebebeb] bg-white">
        <div className="flex items-center justify-between gap-2 p-1.5 rounded-2xl bg-[#f0f0f2]">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-8 h-8 rounded-full bg-[#111111] text-white flex items-center justify-center font-bold text-xs shrink-0">
              {currentUser?.username?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-bold text-[#111111] truncate">
                {currentUser?.full_name || currentUser?.username || 'Operator'}
              </div>
              <div className="text-[10px] text-[#767676] truncate font-medium">
                {currentUser?.role?.replace('_', ' ') || 'Role'}
              </div>
            </div>
          </div>
          <button
            onClick={onLogout}
            title="Log Out"
            className="p-1.5 rounded-full text-[#767676] hover:text-[#e60023] hover:bg-white transition-colors shrink-0"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};

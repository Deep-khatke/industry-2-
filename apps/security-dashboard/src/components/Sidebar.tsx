import React from 'react';
import {
  ShieldAlert,
  Activity,
  AlertTriangle,
  Flame,
  Radio,
  Cpu,
  Settings,
  Share2,
  ChevronDown,
  User,
  LogOut,
  Building2,
  Eye,
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
  const navItems = [
    { id: 'overview', label: 'Security Overview', icon: Activity },
    { id: 'pilot', label: 'ISP Pilot Operations', icon: Eye },
    { id: 'threats', label: 'Threat Monitoring', icon: Flame },
    { id: 'incidents', label: 'Incident Management', icon: AlertTriangle },
    { id: 'actions', label: 'Manual Response Center', icon: ShieldAlert },
    { id: 'health', label: 'ISP Network Health', icon: Radio },
    { id: 'models', label: 'Model Monitoring', icon: Cpu },
    { id: 'federation', label: 'Federated Learning', icon: Share2 },
    { id: 'governance', label: 'Consortium Governance', icon: ShieldAlert },
    { id: 'settings', label: 'Settings & Policy', icon: Settings },
  ];


  const currentTenant = tenants.find((t) => t.tenant_id === selectedTenantId);

  return (
    <aside className="w-64 bg-[#0a0f1d] border-r border-slate-800/80 flex flex-col h-screen fixed left-0 top-0 select-none z-30">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800/80 flex items-center space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.4)]">
          <ShieldAlert className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="text-sm font-bold tracking-wider text-white">FEDERATED CYBER SHIELD</div>
          <div className="text-[10px] text-cyan-400 font-mono tracking-widest uppercase">
            SOC DEFENSE v1.2
          </div>
        </div>
      </div>

      {/* Tenant Switcher */}
      <div className="p-4 border-b border-slate-800/80 bg-slate-900/40">
        <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5 flex items-center space-x-1">
          <Building2 className="w-3 h-3 text-cyan-400" />
          <span>Monitored ISP Tenant</span>
        </label>
        <div className="relative">
          <select
            value={selectedTenantId}
            onChange={(e) => onTenantChange(e.target.value)}
            className="w-full bg-[#111928] text-xs font-semibold text-slate-200 border border-slate-700/80 rounded-lg px-3 py-2 pr-8 appearance-none focus:outline-none focus:border-cyan-500 cursor-pointer shadow-sm hover:border-slate-600"
          >
            {tenants.map((t) => (
              <option key={t.tenant_id} value={t.tenant_id}>
                {t.name} (ASN {t.asn})
              </option>
            ))}
          </select>
          <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
        </div>
        {currentTenant && (
          <div className="mt-1.5 text-[10px] text-slate-500 flex justify-between font-mono">
            <span>{currentTenant.region}</span>
            <span className="text-cyan-400 font-bold">LIVE TELEMETRY</span>
          </div>
        )}
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-cyan-950/70 text-cyan-400 border border-cyan-500/40 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Zero Cost & Status Badge */}
      <div className="px-4 py-2 bg-slate-950/60 border-t border-slate-800/50 text-[11px] font-mono text-slate-400 flex justify-between items-center">
        <span>INFRA COST:</span>
        <span className="text-emerald-400 font-bold">₹0.00 / $0.00</span>
      </div>

      {/* User Profile Footer */}
      <div className="p-3 border-t border-slate-800/80 bg-[#0d131f] flex items-center justify-between">
        <div className="flex items-center space-x-2.5 min-w-0">
          <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
            <User className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="min-w-0">
            <div className="text-xs font-semibold text-slate-200 truncate">
              {currentUser?.full_name || 'Demo Analyst'}
            </div>
            <div className="text-[10px] text-cyan-400 font-mono tracking-wider truncate">
              {currentUser?.role || 'SECURITY_RESPONDER'}
            </div>
          </div>
        </div>
        <button
          onClick={onLogout}
          title="Sign Out"
          className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-950/40 transition-colors"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </aside>
  );
};

import React, { useEffect, useState, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { OverviewPage } from './pages/OverviewPage';
import { PilotOperationsPage } from './pages/PilotOperationsPage';
import { ThreatMonitoringPage } from './pages/ThreatMonitoringPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { ManualResponsePage } from './pages/ManualResponsePage';
import { NetworkHealthPage } from './pages/NetworkHealthPage';
import { ModelMonitoringPage } from './pages/ModelMonitoringPage';
import { FederationPage } from './pages/FederationPage';
import { GovernancePage } from './pages/GovernancePage';
import { SettingsPage } from './pages/SettingsPage';
import { api } from './services/api';
import {
  ActionRecord,
  ActiveModelDetails,
  Exporter,
  FirewallRule,
  Incident,
  IncidentHistory,
  ModelHealth,
  OverviewStats,
  Recommendation,
  ResponsePolicy,
  Tenant,
  User,
} from './types/api';
import { ShieldAlert, Lock, User as UserIcon } from 'lucide-react';

export const App: React.FC = () => {
  // Navigation & Tenant state
  const [currentTab, setCurrentTab] = useState<string>('overview');
  const [selectedTenantId, setSelectedTenantId] = useState<string>('rural-isp-alpha');
  const [tenants, setTenants] = useState<Tenant[]>([]);

  // Auth state
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [loginUsername, setLoginUsername] = useState<string>('responder_alpha');
  const [loginPassword, setLoginPassword] = useState<string>('FcsDemo2026!');
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isLoggingIn, setIsLoggingIn] = useState<boolean>(false);

  // Core Data state
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [incidentHistory, setIncidentHistory] = useState<IncidentHistory[]>([]);
  const [incidentRecs, setIncidentRecs] = useState<Recommendation[]>([]);
  const [actions, setActions] = useState<ActionRecord[]>([]);
  const [firewallRules, setFirewallRules] = useState<FirewallRule[]>([]);
  const [exporters, setExporters] = useState<Exporter[]>([]);
  const [modelDetails, setModelDetails] = useState<ActiveModelDetails | null>(null);
  const [modelHealth, setModelHealth] = useState<ModelHealth | null>(null);
  const [policy, setPolicy] = useState<ResponsePolicy | null>(null);

  // Polling & Replay state
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<number>(5000);
  const [isReplaying, setIsReplaying] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Attempt automatic login with demo credentials on first load
  useEffect(() => {
    const initAuth = async () => {
      try {
        const storedToken = localStorage.getItem('fcs_token');
        if (storedToken) {
          const user = await api.getMe();
          setCurrentUser(user);
          setIsAuthenticated(true);
          return;
        }
        // Auto-login with responder demo account
        const authRes = await api.login('responder_alpha', 'FcsDemo2026!');
        localStorage.setItem('fcs_token', authRes.access_token);
        const me = await api.getMe();
        setCurrentUser(me);
        setIsAuthenticated(true);
      } catch (e) {
        console.warn('Auto-login failed, prompt manual credentials', e);
        setIsAuthenticated(false);
      }
    };
    initAuth();
  }, []);

  // Fetch all primary dashboard data
  const fetchData = useCallback(async () => {
    if (!isAuthenticated) return;
    setIsRefreshing(true);
    try {
      const [
        tenantsRes,
        statsRes,
        incidentsRes,
        actionsRes,
        fwRulesRes,
        expRes,
        modelDetRes,
        modelHlthRes,
        policyRes,
      ] = await Promise.allSettled([
        api.getTenants(),
        api.getOverview(selectedTenantId),
        api.listIncidents({ tenant_id: selectedTenantId, limit: 100 }),
        api.listActions(selectedTenantId, 50),
        api.getActiveFirewallRules(selectedTenantId),
        api.getExportersCoverage(selectedTenantId),
        api.getActiveModel(),
        api.getModelHealth(),
        api.getResponsePolicy(),
      ]);

      if (tenantsRes.status === 'fulfilled') setTenants(tenantsRes.value);
      if (statsRes.status === 'fulfilled') setStats(statsRes.value);
      if (incidentsRes.status === 'fulfilled') {
        setIncidents(incidentsRes.value.incidents);
        // Refresh selected incident if open
        if (selectedIncident) {
          const updated = incidentsRes.value.incidents.find(
            (i) => i.incident_id === selectedIncident.incident_id
          );
          if (updated) setSelectedIncident(updated);
        }
      }
      if (actionsRes.status === 'fulfilled') setActions(actionsRes.value);
      if (fwRulesRes.status === 'fulfilled') setFirewallRules(fwRulesRes.value);
      if (expRes.status === 'fulfilled') setExporters(expRes.value);
      if (modelDetRes.status === 'fulfilled') setModelDetails(modelDetRes.value);
      if (modelHlthRes.status === 'fulfilled') setModelHealth(modelHlthRes.value);
      if (policyRes.status === 'fulfilled') setPolicy(policyRes.value);
    } catch (e) {
      console.error('Error fetching dashboard data:', e);
    } finally {
      setIsRefreshing(false);
    }
  }, [isAuthenticated, selectedTenantId, selectedIncident]);

  // Initial fetch and tenant changes
  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    }
  }, [isAuthenticated, selectedTenantId, fetchData]);

  // Auto-polling interval
  useEffect(() => {
    if (!isAuthenticated || refreshInterval <= 0) return;
    const interval = setInterval(() => {
      fetchData();
    }, refreshInterval);
    return () => clearInterval(interval);
  }, [isAuthenticated, refreshInterval, fetchData]);

  // Load history and recommendations when selectedIncident changes
  useEffect(() => {
    if (!selectedIncident) {
      setIncidentHistory([]);
      setIncidentRecs([]);
      return;
    }
    const loadIncidentDetails = async () => {
      try {
        const [hist, recs] = await Promise.all([
          api.getIncidentHistory(selectedIncident.incident_id),
          api.getIncidentRecommendations(selectedIncident.incident_id),
        ]);
        setIncidentHistory(hist);
        setIncidentRecs(recs);
      } catch (e) {
        console.error('Error loading incident details:', e);
      }
    };
    loadIncidentDetails();
  }, [selectedIncident]);

  // Handle Login
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoggingIn(true);
    setLoginError(null);
    try {
      const res = await api.login(loginUsername, loginPassword);
      localStorage.setItem('fcs_token', res.access_token);
      const me = await api.getMe();
      setCurrentUser(me);
      setIsAuthenticated(true);
      showToast(`Welcome back, ${me.full_name}!`);
    } catch (err: any) {
      setLoginError(err.message || 'Login failed. Please check credentials.');
    } finally {
      setIsLoggingIn(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('fcs_token');
    setIsAuthenticated(false);
    setCurrentUser(null);
  };

  // Handle Replay Scenario Trigger
  const handleTriggerReplay = async (scenario: 'normal' | 'suspicious' | 'scanning') => {
    setIsReplaying(true);
    try {
      const res = await api.startReplay(scenario, selectedTenantId);
      showToast(`Replay '${scenario}' completed: ${res.replayed_flows} flows processed.`);
      await fetchData();
    } catch (e: any) {
      showToast(`Replay failed: ${e.message}`);
    } finally {
      setIsReplaying(false);
    }
  };

  // Handle Database Reset
  const handleResetDb = async () => {
    if (!confirm('Reset demonstration database to clean baseline state?')) return;
    setIsReplaying(true);
    try {
      await api.resetDemoDatabase();
      setSelectedIncident(null);
      showToast('Database reset to clean state successfully.');
      await fetchData();
    } catch (e: any) {
      showToast(`Reset failed: ${e.message}`);
    } finally {
      setIsReplaying(false);
    }
  };

  // Handle Incident Status Update
  const handleUpdateStatus = async (incidentId: string, status: string, notes?: string) => {
    await api.updateIncidentStatus(incidentId, status, notes);
    showToast(`Incident marked as ${status}`);
    await fetchData();
  };

  // Handle Manual Action Approval & Execution
  const handleApproveAction = async (payload: {
    incident_id: string;
    action_type: string;
    target: string;
    duration_seconds: number;
    idempotency_key: string;
    scope: string;
    recommendation_id?: string;
  }) => {
    const res = await api.approveAndExecuteAction(payload.incident_id, payload);
    showToast(`Defensive action executed & verified in simulator! (Action ID: ${res.action_id})`);
    await fetchData();
  };

  // Handle Action Rollback
  const handleRollbackAction = async (actionId: string) => {
    await api.rollbackAction(actionId);
    showToast(`Action ${actionId} revoked and rolled back in simulator.`);
    await fetchData();
  };

  // Login View
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-[#070b12] flex items-center justify-center p-4">
        <div className="cyber-card p-8 max-w-md w-full space-y-6 border-cyan-500/50 shadow-[0_0_30px_rgba(6,182,212,0.25)]">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center mx-auto shadow-[0_0_15px_rgba(6,182,212,0.5)]">
              <ShieldAlert className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-xl font-bold text-white tracking-wider">
              FEDERATED CYBER SHIELD
            </h1>
            <p className="text-xs text-cyan-400 font-mono tracking-widest uppercase">
              SECURITY OPERATIONS CENTER (SOC) v1.2
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4 text-xs font-mono">
            {loginError && (
              <div className="p-3 rounded-lg bg-red-950/80 border border-red-700 text-red-300">
                {loginError}
              </div>
            )}

            <div>
              <label className="text-slate-400 uppercase text-[10px] block mb-1">
                Username
              </label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  required
                />
              </div>
            </div>

            <div>
              <label className="text-slate-400 uppercase text-[10px] block mb-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500"
                  required
                />
              </div>
            </div>

            <div className="p-3 bg-slate-950/80 rounded border border-slate-800 text-[10px] text-slate-400 space-y-1">
              <span className="text-cyan-400 font-bold block">Seeded Demonstration Accounts:</span>
              <div>• responder_alpha / FcsDemo2026! (Security Responder)</div>
              <div>• analyst_alpha / FcsDemo2026! (Security Analyst)</div>
              <div>• admin_alpha / FcsDemo2026! (Tenant Admin)</div>
            </div>

            <button
              type="submit"
              disabled={isLoggingIn}
              className="w-full py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-black font-bold text-xs uppercase tracking-wider transition-all disabled:opacity-50 shadow-[0_0_15px_rgba(6,182,212,0.3)]"
            >
              {isLoggingIn ? 'Authenticating...' : 'Sign In to SOC'}
            </button>
          </form>

          <div className="text-center text-[10px] font-mono text-slate-500">
            Phase 4 Development Environment • Strictly ₹0 / $0 Budget Constraint
          </div>
        </div>
      </div>
    );
  }

  const currentTenantObj = tenants.find((t) => t.tenant_id === selectedTenantId);

  // Tab Titles
  const tabTitles: Record<string, { title: string; subtitle: string }> = {
    overview: {
      title: 'Security Operations Overview',
      subtitle: `Real-time monitoring telemetry for ${currentTenantObj?.name || 'Selected ISP'}`,
    },
    threats: {
      title: 'Real-Time Threat Detection Stream',
      subtitle: 'Continuous event window aggregation and ML anomaly scoring',
    },
    incidents: {
      title: 'Incident Management & Investigation',
      subtitle: 'Durable persistent incident lifecycle and audit trail',
    },
    actions: {
      title: 'Manual Response Policy Center',
      subtitle: 'Authorized administrator approval and isolated software firewall simulator',
    },
    health: {
      title: 'ISP Network Health & Exporters',
      subtitle: 'NetFlow / IPFIX exporter ingestion freshness and completeness',
    },
    models: {
      title: 'ML Model Monitoring & Provenance',
      subtitle: 'Phase 3 LightGBM candidate evaluation, feature contracts, and runtime limits',
    },
    federation: {
      title: 'Federated Learning Operations',
      subtitle: 'Flower SecAgg+ & Opacus DP-SGD Multi-Tenant Privacy Engine',
    },
    governance: {
      title: 'Consortium Trust & Blockchain Governance',
      subtitle: 'Hyperledger Fabric SmartBFT, NIST FIPS 204 ML-DSA-65 & Model Supply Chain',
    },
    settings: {
      title: 'Tenant Settings & Response Safety',
      subtitle: 'RBAC permissions matrix, protected infrastructure, and policy rules',
    },
  };

  return (
    <div className="min-h-screen bg-[#070b12] text-slate-100 flex">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 bg-slate-900 border border-cyan-500 text-cyan-300 text-xs px-4 py-3 rounded-xl shadow-[0_0_20px_rgba(6,182,212,0.4)] font-mono animate-bounce flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Fixed Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        tenants={tenants}
        selectedTenantId={selectedTenantId}
        onTenantChange={setSelectedTenantId}
        currentUser={currentUser}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <div className="flex-1 ml-64 flex flex-col min-w-0">
        <Header
          title={tabTitles[currentTab]?.title || 'Security Operations'}
          subtitle={tabTitles[currentTab]?.subtitle}
          onRefresh={fetchData}
          isRefreshing={isRefreshing}
          refreshInterval={refreshInterval}
          onRefreshIntervalChange={setRefreshInterval}
          onTriggerReplay={handleTriggerReplay}
          onResetDb={handleResetDb}
          isReplaying={isReplaying}
        />

        <main className="flex-1 p-6 overflow-y-auto">
          {currentTab === 'overview' && (
            <OverviewPage
              stats={stats}
              recentIncidents={incidents}
              onSelectIncident={(inc) => {
                setSelectedIncident(inc);
                setCurrentTab('incidents');
              }}
              onNavigateToIncidents={() => setCurrentTab('incidents')}
              onNavigateToResponse={() => setCurrentTab('actions')}
            />
          )}

          {currentTab === 'pilot' && (
            <PilotOperationsPage selectedTenantId={selectedTenantId} />
          )}

          {currentTab === 'threats' && (
            <ThreatMonitoringPage
              incidents={incidents}
              onSelectIncident={(inc) => {
                setSelectedIncident(inc);
                setCurrentTab('incidents');
              }}
            />
          )}

          {currentTab === 'incidents' && (
            <IncidentsPage
              incidents={incidents}
              selectedIncident={selectedIncident}
              onSelectIncident={setSelectedIncident}
              onUpdateStatus={handleUpdateStatus}
              incidentHistory={incidentHistory}
              recommendations={incidentRecs}
              onNavigateToResponseWithIncident={(inc) => {
                setSelectedIncident(inc);
                setCurrentTab('actions');
              }}
            />
          )}

          {currentTab === 'actions' && (
            <ManualResponsePage
              recommendations={incidentRecs.length > 0 ? incidentRecs : []}
              actions={actions}
              firewallRules={firewallRules}
              activeIncidents={incidents.filter(
                (i) => i.status !== 'RESOLVED' && i.status !== 'CLOSED' && i.status !== 'FALSE_POSITIVE'
              )}
              currentUser={currentUser}
              onApproveAction={handleApproveAction}
              onRollbackAction={handleRollbackAction}
              targetIncident={selectedIncident}
            />
          )}

          {currentTab === 'health' && (
            <NetworkHealthPage
              exporters={exporters}
              stats={stats}
              currentTenant={currentTenantObj}
            />
          )}

          {currentTab === 'models' && (
            <ModelMonitoringPage
              modelDetails={modelDetails}
              modelHealth={modelHealth}
            />
          )}

          {currentTab === 'federation' && <FederationPage />}

          {currentTab === 'governance' && <GovernancePage />}

          {currentTab === 'settings' && (
            <SettingsPage
              currentTenant={currentTenantObj}
              currentUser={currentUser}
              policy={policy}
            />
          )}
        </main>
      </div>
    </div>
  );
};

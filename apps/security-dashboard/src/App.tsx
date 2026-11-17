import React, { useEffect, useState, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { ErrorBoundary } from './components/ErrorBoundary';
import { OverviewPage } from './pages/OverviewPage';
import { PilotOperationsPage } from './pages/PilotOperationsPage';
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
  const [allRecommendations, setAllRecommendations] = useState<Recommendation[]>([]);
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
        recsRes,
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
        api.listRecommendations(selectedTenantId),
      ]);

      if (tenantsRes.status === 'fulfilled') setTenants(Array.isArray(tenantsRes.value) ? tenantsRes.value : []);
      if (statsRes.status === 'fulfilled') setStats(statsRes.value);
      if (incidentsRes.status === 'fulfilled') {
        const incList = incidentsRes.value?.incidents || (Array.isArray(incidentsRes.value) ? incidentsRes.value : []);
        setIncidents(incList);
        // Refresh selected incident if open
        if (selectedIncident) {
          const updated = incList.find(
            (i: Incident) => i.incident_id === selectedIncident.incident_id
          );
          if (updated) setSelectedIncident(updated);
        }
      }
      if (actionsRes.status === 'fulfilled') setActions(Array.isArray(actionsRes.value) ? actionsRes.value : []);
      if (fwRulesRes.status === 'fulfilled') setFirewallRules(Array.isArray(fwRulesRes.value) ? fwRulesRes.value : []);
      if (expRes.status === 'fulfilled') {
        const expData = expRes.value;
        if (Array.isArray(expData)) {
          setExporters(expData);
        } else if (expData && Array.isArray((expData as any).exporters)) {
          setExporters((expData as any).exporters);
        } else {
          setExporters([]);
        }
      }
      if (modelDetRes.status === 'fulfilled') setModelDetails(modelDetRes.value);
      if (modelHlthRes.status === 'fulfilled') setModelHealth(modelHlthRes.value);
      if (policyRes.status === 'fulfilled') setPolicy(policyRes.value);
      if (recsRes.status === 'fulfilled') {
        setAllRecommendations(Array.isArray(recsRes.value) ? recsRes.value : []);
      }
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
      <div className="min-h-screen bg-[#f7f7f8] flex items-center justify-center p-4 font-sans">
        <div className="bg-white border border-[#ebebeb] p-8 max-w-sm w-full space-y-6 rounded-3xl shadow-xl">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 rounded-2xl bg-[#e60023] flex items-center justify-center mx-auto text-white shadow-md">
              <ShieldAlert className="w-6 h-6 fill-white/20" />
            </div>
            <h1 className="text-lg font-extrabold text-[#111111] tracking-tight">
              Federated Cyber Shield
            </h1>
            <p className="text-xs text-[#767676] font-medium tracking-wide">
              Consortium Security Operations Console
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4 text-xs">
            {loginError && (
              <div className="p-3 rounded-2xl bg-[#fff0f2] border border-[#fecdd3] text-[#e60023] text-xs font-semibold">
                {loginError}
              </div>
            )}

            <div>
              <label className="text-[#767676] uppercase text-[10px] font-bold block mb-1.5 px-1">
                Username
              </label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-[#767676] absolute left-3.5 top-3" />
                <input
                  type="text"
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                  className="w-full bg-[#f0f0f2] border border-transparent focus:border-[#e60023] focus:bg-white rounded-full pl-10 pr-4 py-2.5 text-[#111111] font-medium focus:outline-none transition-colors"
                  required
                />
              </div>
            </div>

            <div>
              <label className="text-[#767676] uppercase text-[10px] font-bold block mb-1.5 px-1">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-[#767676] absolute left-3.5 top-3" />
                <input
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="w-full bg-[#f0f0f2] border border-transparent focus:border-[#e60023] focus:bg-white rounded-full pl-10 pr-4 py-2.5 text-[#111111] font-medium focus:outline-none transition-colors"
                  required
                />
              </div>
            </div>

            <div className="p-3 bg-[#fafafa] rounded-2xl border border-[#ebebeb] text-[11px] text-[#767676] space-y-1.5">
              <span className="text-[#111111] font-bold block uppercase text-[10px]">Quick Demo Accounts:</span>
              <div className="flex flex-wrap gap-1.5 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setLoginUsername('responder_alpha');
                    setLoginPassword('FcsDemo2026!');
                  }}
                  className="px-3 py-1 rounded-full bg-white hover:bg-[#fff0f2] hover:text-[#e60023] border border-[#ebebeb] text-[#111111] font-mono font-medium shadow-xs transition-colors"
                >
                  responder_alpha
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setLoginUsername('analyst_alpha');
                    setLoginPassword('FcsDemo2026!');
                  }}
                  className="px-3 py-1 rounded-full bg-white hover:bg-[#fff0f2] hover:text-[#e60023] border border-[#ebebeb] text-[#111111] font-mono font-medium shadow-xs transition-colors"
                >
                  analyst_alpha
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setLoginUsername('admin_alpha');
                    setLoginPassword('FcsDemo2026!');
                  }}
                  className="px-3 py-1 rounded-full bg-white hover:bg-[#fff0f2] hover:text-[#e60023] border border-[#ebebeb] text-[#111111] font-mono font-medium shadow-xs transition-colors"
                >
                  admin_alpha
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoggingIn}
              className="w-full py-3 rounded-full bg-[#e60023] hover:bg-[#bd081c] text-white font-bold text-xs transition-all disabled:opacity-50 shadow-md hover:scale-[1.01]"
            >
              {isLoggingIn ? 'Authenticating...' : 'Sign In to Security Operations'}
            </button>
          </form>

          <div className="text-center text-[10px] font-mono text-[#767676] pt-1 border-t border-zinc-100">
            Controlled Sandbox • Zero-Cost Policy Verified
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
    <div className="min-h-screen bg-[#f7f7f8] text-[#111111] flex font-sans">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-white border border-[#ebebeb] text-[#111111] text-xs px-4 py-3 rounded-full shadow-xl font-sans flex items-center gap-2.5">
          <span className="w-2 h-2 rounded-full bg-[#e60023] shrink-0" />
          <span className="font-semibold">{toastMessage}</span>
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
          <ErrorBoundary>
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
                recommendations={
                  selectedIncident
                    ? (incidentRecs.length > 0
                        ? incidentRecs
                        : allRecommendations.filter((r) => r.incident_id === selectedIncident.incident_id))
                    : allRecommendations
                }
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
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
};

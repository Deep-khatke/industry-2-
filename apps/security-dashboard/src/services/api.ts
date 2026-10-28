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
} from '../types/api';

const API_BASE = '/v1';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('fcs_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let errorDetail = 'Unknown API Error';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      errorDetail = response.statusText || `HTTP ${response.status}`;
    }
    throw new ApiError(errorDetail, response.status);
  }

  return response.json();
}

export const api = {
  // Auth
  login: async (username: string, password: string) => {
    return request<{ access_token: string; user_id: string; username: string; tenant_id: string | null; role: string; full_name: string }>('/auth/token', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  },

  getMe: async (): Promise<User> => {
    return request<User>('/auth/me');
  },

  // Overview & Tenants
  getOverview: async (tenantId?: string): Promise<OverviewStats> => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return request<OverviewStats>(`/overview${q}`);
  },

  getTenants: async (): Promise<Tenant[]> => {
    return request<Tenant[]>('/tenants');
  },

  getExportersCoverage: async (tenantId?: string): Promise<Exporter[]> => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return request<Exporter[]>(`/coverage${q}`);
  },

  // Incidents
  listIncidents: async (params?: { tenant_id?: string; status?: string; severity?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.tenant_id) query.set('tenant_id', params.tenant_id);
    if (params?.status) query.set('status', params.status);
    if (params?.severity) query.set('severity', params.severity);
    if (params?.limit) query.set('limit', params.limit.toString());
    if (params?.offset) query.set('offset', params.offset.toString());
    return request<{ tenant_id: string; total: number; limit: number; offset: number; incidents: Incident[] }>(`/incidents?${query.toString()}`);
  },

  getIncident: async (incidentId: string): Promise<Incident> => {
    return request<Incident>(`/incidents/${incidentId}`);
  },

  updateIncidentStatus: async (incidentId: string, status: string, notes?: string): Promise<Incident> => {
    return request<Incident>(`/incidents/${incidentId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, notes }),
    });
  },

  getIncidentHistory: async (incidentId: string): Promise<IncidentHistory[]> => {
    return request<IncidentHistory[]>(`/incidents/${incidentId}/history`);
  },

  getIncidentRecommendations: async (incidentId: string): Promise<Recommendation[]> => {
    return request<Recommendation[]>(`/incidents/${incidentId}/recommendations`);
  },

  // Actions & Firewall Simulator
  approveAndExecuteAction: async (incidentId: string, payload: {
    action_type: string;
    target: string;
    duration_seconds: number;
    idempotency_key: string;
    scope?: string;
    recommendation_id?: string;
  }): Promise<ActionRecord> => {
    return request<ActionRecord>(`/incidents/${incidentId}/actions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listActions: async (tenantId?: string, limit = 50): Promise<ActionRecord[]> => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}&limit=${limit}` : `?limit=${limit}`;
    return request<ActionRecord[]>(`/actions${q}`);
  },

  getAction: async (actionId: string): Promise<ActionRecord> => {
    return request<ActionRecord>(`/actions/${actionId}`);
  },

  rollbackAction: async (actionId: string): Promise<ActionRecord> => {
    return request<ActionRecord>(`/actions/${actionId}/rollback`, {
      method: 'POST',
    });
  },

  getActiveFirewallRules: async (tenantId?: string): Promise<FirewallRule[]> => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return request<FirewallRule[]>(`/firewall/rules${q}`);
  },

  // Detection & Models
  getDetectionStatus: async (): Promise<any> => {
    return request<any>('/detection/status');
  },

  getActiveModel: async (): Promise<ActiveModelDetails> => {
    return request<ActiveModelDetails>('/models/active');
  },

  getModelHealth: async (): Promise<ModelHealth> => {
    return request<ModelHealth>('/models/health');
  },

  getDetectionBundle: async (): Promise<any> => {
    return request<any>('/detection/bundle');
  },

  activateDetectionBundle: async (payload: any): Promise<any> => {
    return request<any>('/detection/bundle/activate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  rollbackDetectionBundle: async (): Promise<any> => {
    return request<any>('/detection/bundle/rollback', {
      method: 'POST',
    });
  },

  getRoutingDecisions: async (limit = 20): Promise<any[]> => {
    return request<any[]>(`/detection/routing-decisions?limit=${limit}`);
  },

  getISPAnomalyStatus: async (): Promise<any> => {
    return request<any>('/detection/isp-anomaly-status');
  },

  getRegisteredModels: async (): Promise<any[]> => {
    return request<any[]>('/detection/models');
  },

  // Policy
  getResponsePolicy: async (): Promise<ResponsePolicy> => {
    return request<ResponsePolicy>('/response-policy');
  },

  // Dev & Demo
  startReplay: async (scenario: 'normal' | 'suspicious' | 'scanning' | 'mixed', tenantId: string) => {
    return request<{ scenario: string; tenant_id: string; replayed_flows: number; processed_count: number; incidents_created: number; replayed_at: string }>('/dev/replay/start', {
      method: 'POST',
      body: JSON.stringify({ scenario, tenant_id: tenantId }),
    });
  },

  resetDemoDatabase: async () => {
    return request<{ status: string; message: string }>('/dev/reset', {
      method: 'POST',
    });
  },

  // Phase 9 Pilot Operations
  getPilotStatus: async (tenantId?: string) => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return request<any>(`/pilot/status${q}`);
  },

  getPilotReadiness: async (tenantId?: string) => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return request<any>(`/pilot/readiness${q}`);
  },

  getPilotRequirements: async () => {
    return request<any>('/pilot/requirements');
  },

  getPilotExporters: async () => {
    return request<any>('/pilot/exporters');
  },

  getExporterCompatibility: async (exporterKey: string) => {
    return request<any>(`/pilot/exporters/${encodeURIComponent(exporterKey)}/compatibility`);
  },

  getPilotCoverage: async (tenantId?: string) => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return request<any>(`/pilot/coverage${q}`);
  },

  getPilotShadowMetrics: async (tenantId?: string) => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return request<any>(`/pilot/shadow-metrics${q}`);
  },

  getPilotDailyReports: async (tenantId?: string) => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return request<any>(`/pilot/daily-reports${q}`);
  },

  getPilotAnalystWorkload: async (tenantId?: string) => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return request<any>(`/pilot/analyst-workload${q}`);
  },

  getPilotSafetyStatus: async () => {
    return request<any>('/pilot/safety-status');
  },

  getPilotHealth: async (tenantId?: string) => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return request<any>(`/pilot/health${q}`);
  },

  getPilotComprehensiveReport: async (tenantId?: string) => {
    const q = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return request<any>(`/pilot/report${q}`);
  },

  configurePilot: async (pilotId: string, targetState: string, reason: string) => {
    return request<any>('/pilot/configure', {
      method: 'POST',
      body: JSON.stringify({ pilot_id: pilotId, target_state: targetState, reason }),
    });
  },

  submitAnalystFeedback: async (feedback: { incident_id: string; disposition: string; review_duration_seconds: number; notes: string; confidence_level?: number }) => {
    return request<any>('/pilot/analyst-feedback', {
      method: 'POST',
      body: JSON.stringify(feedback),
    });
  },

  startPilotSyntheticReplay: async (scenario = 'SYNTHETIC_7_DAY') => {
    return request<any>(`/dev/pilot/replay?scenario=${encodeURIComponent(scenario)}`, {
      method: 'POST',
    });
  },
};


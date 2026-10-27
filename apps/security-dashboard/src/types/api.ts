export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';

export type IncidentStatus =
  | 'NEW'
  | 'ACKNOWLEDGED'
  | 'INVESTIGATING'
  | 'ACTION_PENDING'
  | 'MITIGATED'
  | 'RESOLVED'
  | 'FALSE_POSITIVE'
  | 'CLOSED';

export type ActionStatus =
  | 'REQUESTED'
  | 'PENDING'
  | 'APPLIED'
  | 'VERIFIED'
  | 'FAILED'
  | 'ROLLED_BACK'
  | 'EXPIRED';

export interface User {
  user_id: string;
  username: string;
  tenant_id: string | null;
  role: 'TENANT_ADMIN' | 'SECURITY_ANALYST' | 'SECURITY_RESPONDER' | 'READ_ONLY' | 'PLATFORM_ADMIN';
  full_name: string;
}

export interface Tenant {
  tenant_id: string;
  name: string;
  region: string;
  asn: number;
}

export interface Incident {
  incident_id: string;
  tenant_id: string;
  grouping_key: string;
  title: string;
  attack_category: string;
  severity: Severity;
  status: IncidentStatus;
  risk_score: number;
  target_ip: string;
  target_port: number;
  evidence_json: string;
  assigned_to?: string | null;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentHistory {
  history_id: string;
  incident_id: string;
  tenant_id: string;
  actor_id: string;
  previous_status: IncidentStatus;
  new_status: IncidentStatus;
  change_notes: string;
  created_at: string;
}

export interface Recommendation {
  recommendation_id: string;
  incident_id: string;
  tenant_id: string;
  action_type: 'TEMPORARY_BLOCK' | 'RATE_LIMIT';
  target: string;
  scope: string;
  recommended_duration_seconds: number;
  reason: string;
  risk_level: string;
  status: string;
  created_at: string;
}

export interface ActionRecord {
  action_id: string;
  recommendation_id?: string | null;
  incident_id: string;
  tenant_id: string;
  approved_by: string;
  approval_timestamp: string;
  action_type: string;
  target: string;
  scope: string;
  duration_seconds: number;
  applied_timestamp?: string | null;
  expiry_timestamp?: string | null;
  status: ActionStatus;
  idempotency_key: string;
  verification_details_json?: string | null;
  failure_reason?: string | null;
  created_at: string;
}

export interface FirewallRule {
  rule_id: string;
  action_id: string;
  tenant_id: string;
  target: string;
  rule_type: string;
  parameters_json: string;
  applied_at: string;
  expires_at: string;
  status: string;
  created_at: string;
}

export interface Exporter {
  exporter_id: string;
  tenant_id: string;
  name: string;
  ip_address: string;
  status: 'HEALTHY' | 'DEGRADED' | 'STALE' | 'OFFLINE';
  last_seen_at?: string | null;
  records_received: number;
}

export interface OverviewStats {
  tenant_id: string;
  timestamp: string;
  flow_metrics: {
    total_monitored_flows: number;
    recent_flows_1h: number;
    freshness: string;
  };
  incident_metrics: {
    active_incidents: number;
    critical_incidents: number;
    high_incidents: number;
    total_incidents: number;
    status_breakdown: Record<string, number>;
    category_breakdown: Record<string, number>;
  };
  exporter_summary: {
    total_configured: number;
    healthy: number;
    degraded: number;
    stale: number;
  };
  detection_summary: {
    active_model_id: string;
    model_version: string;
    model_status: string;
    inference_mode: string;
    response_mode: string;
  };
}

export interface ModelHealth {
  model_id: string;
  status: string;
  registry_dir: string;
  last_error: string | null;
  deployable_features_count: number;
  fallback_mode: string;
  active_bundle_id?: string;
  bundle_digest?: string;
  general_model?: string;
  anomaly_model?: string;
  specialist_models?: string[];
  zero_cost_runtime?: string;
  security_invariant?: string;
}

export interface DetectionBundle {
  bundle_id: string;
  version: string;
  general_model_id: string;
  anomaly_model_id: string;
  specialist_model_ids: string[];
  model_hashes: Record<string, string>;
  bundle_digest: string;
  authorized_by: string;
  status: string;
  created_at: string;
  activated_at?: string | null;
}

export interface RoutingDecision {
  decision_id: string;
  tenant_id: string;
  window_id?: string | null;
  level1_general_score: number;
  level1_anomaly_score: number;
  should_route: number | boolean;
  routed_models_json?: string;
  bypassed_models_json?: string;
  trigger_reasons_json?: string;
  routed_models?: string[];
  bypassed_models?: string[];
  trigger_reasons?: string[];
  routing_latency_us: number;
  created_at: string;
}

export interface ISPAnomalyStatus {
  tenant_id: string;
  baseline_status: 'CALIBRATED' | 'WARMUP';
  isolation_boundary: string;
  anomaly_model_family: string;
  contamination_floor: number;
  monitored_windows_count: number;
  cross_tenant_access: string;
}

export interface ModelScoreEvidence {
  model_id: string;
  model_type: string;
  version: string;
  raw_score: number;
  calibrated_probability: number;
  confidence: number;
  threshold_applied: number;
  prediction: number;
  predicted_label: string;
  is_uncertain: boolean;
  status: string;
  latency_microseconds: number;
  features_used?: string[];
  reason_codes?: string[];
}

export interface MultiModelEvidence {
  general_score?: ModelScoreEvidence;
  anomaly_score?: ModelScoreEvidence;
  specialist_scores?: ModelScoreEvidence[];
  routing_decision?: {
    routed_models?: string[];
    bypassed_models?: string[];
    trigger_reasons?: string[];
    routing_latency_us?: number;
  };
  fusion_method?: string;
  weights_applied?: Record<string, number>;
  uncertainty_flag?: boolean;
  reason_codes?: string[];
  total_latency_us?: number;
  fallback?: string;
  mode?: string;
}

export interface ActiveModelDetails {
  model_id: string;
  status: string;
  model_type: string;
  training_phase: string;
  pr_auc: number;
  f1_score: number;
  inference_latency_p95_ms: number;
  deployable_feature_count: number;
  deployable_feature_schema: Array<{
    name: string;
    type: string;
    description: string;
  }>;
  zero_cost_runtime: string;
  security_invariant: string;
}

export interface ResponsePolicy {
  response_mode: 'MANUAL';
  auto_response_enabled: false;
  auto_response_status: string;
  allowed_manual_actions: string[];
  min_duration_seconds: number;
  max_duration_seconds: number;
  protected_ip_ranges: string[];
  execution_boundary: string;
  requires_roles: string[];
  simulation_disclaimer: string;
  idempotency_enforced: boolean;
  rollback_supported: boolean;
}

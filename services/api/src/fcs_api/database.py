"""Database schema, connection management, and seeding for FCS Phase 4."""

import sqlite3
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .config import settings

CREATE_TABLES_SQL = """
-- 1. Tenants Table
CREATE TABLE IF NOT EXISTS tenants (
    tenant_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    region TEXT NOT NULL DEFAULT 'ap-south-1',
    max_events_per_sec INTEGER NOT NULL DEFAULT 10000,
    created_at TEXT NOT NULL
);

-- 2. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    tenant_id TEXT,
    role TEXT NOT NULL,
    full_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 3. Exporters Table
CREATE TABLE IF NOT EXISTS exporters (
    exporter_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    observation_domain_id INTEGER NOT NULL DEFAULT 0,
    sample_rate INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'HEALTHY',
    last_seen_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 4. Ingested Flow Events Table
CREATE TABLE IF NOT EXISTS flow_events (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    exporter_id TEXT NOT NULL,
    observation_domain INTEGER NOT NULL DEFAULT 0,
    sequence INTEGER NOT NULL DEFAULT 0,
    event_time TEXT NOT NULL,
    ingest_time TEXT NOT NULL,
    protocol TEXT NOT NULL,
    src_port INTEGER,
    dst_port INTEGER,
    byte_count INTEGER NOT NULL,
    packet_count INTEGER NOT NULL,
    flow_duration_ms REAL NOT NULL,
    tcp_flags INTEGER,
    raw_json TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 5. Feature Windows Table
CREATE TABLE IF NOT EXISTS feature_windows (
    window_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    flow_count INTEGER NOT NULL,
    byte_sum INTEGER NOT NULL,
    packet_sum INTEGER NOT NULL,
    avg_duration_ms REAL NOT NULL,
    feature_vector_json TEXT NOT NULL,
    is_complete INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 6. Detection Scores Table
CREATE TABLE IF NOT EXISTS detection_scores (
    score_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    window_id TEXT,
    model_id TEXT NOT NULL,
    model_version TEXT NOT NULL,
    raw_score REAL NOT NULL,
    calibrated_probability REAL NOT NULL,
    threshold_applied REAL NOT NULL,
    prediction INTEGER NOT NULL,
    predicted_label TEXT NOT NULL,
    is_uncertain INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'SCORED',
    latency_microseconds REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 7. Incidents Table
CREATE TABLE IF NOT EXISTS incidents (
    incident_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    grouping_key TEXT NOT NULL,
    title TEXT NOT NULL,
    attack_category TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'NEW',
    risk_score REAL NOT NULL,
    target_ip TEXT,
    target_port INTEGER,
    evidence_json TEXT NOT NULL,
    model_version TEXT,
    rule_matches_json TEXT NOT NULL,
    assigned_to TEXT,
    acknowledged_at TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 8. Incident History Table
CREATE TABLE IF NOT EXISTS incident_history (
    history_id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    previous_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    change_notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id),
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 9. Recommendations Table
CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'EDGE_FIREWALL',
    recommended_duration_seconds INTEGER NOT NULL DEFAULT 900,
    reason TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    created_at TEXT NOT NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id),
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 10. Action Journal (Manual Response Log) Table
CREATE TABLE IF NOT EXISTS action_journal (
    action_id TEXT PRIMARY KEY,
    recommendation_id TEXT,
    incident_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    approved_by TEXT NOT NULL,
    approval_timestamp TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target TEXT NOT NULL,
    scope TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    applied_timestamp TEXT,
    expiry_timestamp TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    idempotency_key TEXT UNIQUE NOT NULL,
    verification_details_json TEXT,
    failure_reason TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(incident_id) REFERENCES incidents(incident_id),
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 11. Simulated Firewall Rules Table
CREATE TABLE IF NOT EXISTS simulated_firewall_rules (
    rule_id TEXT PRIMARY KEY,
    action_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    target TEXT NOT NULL,
    rule_type TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    FOREIGN KEY(action_id) REFERENCES action_journal(action_id),
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 12. Notification Outbox Table
CREATE TABLE IF NOT EXISTS notification_outbox (
    outbox_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    retries INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 13. Audit Events Table
CREATE TABLE IF NOT EXISTS audit_events (
    audit_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    event_action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 14. Service Health Table
CREATE TABLE IF NOT EXISTS service_health (
    component_name TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'HEALTHY',
    details_json TEXT NOT NULL,
    last_check_at TEXT NOT NULL
);

-- 15. Detection Bundles Table (Phase 5 FCS-HMD)
CREATE TABLE IF NOT EXISTS detection_bundles (
    bundle_id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    general_model_id TEXT NOT NULL,
    anomaly_model_id TEXT NOT NULL,
    specialist_model_ids_json TEXT NOT NULL,
    model_hashes_json TEXT NOT NULL,
    bundle_digest TEXT NOT NULL,
    authorized_by TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    created_at TEXT NOT NULL,
    activated_at TEXT
);

-- 16. Routing Decisions Table (Phase 5 FCS-HMD)
CREATE TABLE IF NOT EXISTS routing_decisions (
    decision_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    window_id TEXT,
    level1_general_score REAL NOT NULL,
    level1_anomaly_score REAL NOT NULL,
    should_route INTEGER NOT NULL,
    routed_models_json TEXT NOT NULL,
    bypassed_models_json TEXT NOT NULL,
    trigger_reasons_json TEXT NOT NULL,
    routing_latency_us REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- 17. Multi-Model Individual Scores Table (Phase 5 FCS-HMD)
CREATE TABLE IF NOT EXISTS model_scores (
    score_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    window_id TEXT,
    model_id TEXT NOT NULL,
    model_type TEXT NOT NULL,
    version TEXT NOT NULL,
    raw_score REAL NOT NULL,
    calibrated_probability REAL NOT NULL,
    threshold_applied REAL NOT NULL,
    prediction INTEGER NOT NULL,
    predicted_label TEXT NOT NULL,
    is_uncertain INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'SCORED',
    latency_microseconds REAL NOT NULL DEFAULT 0.0,
    reason_codes_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id)
);

-- Indexes for Fast Tenant Queries & Time Range Filtering
CREATE INDEX IF NOT EXISTS idx_flow_tenant_time ON flow_events(tenant_id, event_time);
CREATE INDEX IF NOT EXISTS idx_incidents_tenant_status ON incidents(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_incidents_tenant_time ON incidents(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_action_tenant ON action_journal(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_fw_active ON simulated_firewall_rules(tenant_id, status, expires_at);
CREATE INDEX IF NOT EXISTS idx_routing_tenant ON routing_decisions(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_model_scores_window ON model_scores(tenant_id, window_id);
"""

_local = threading.local()


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Retrieve or create a thread-local SQLite connection."""
    target_path = str(db_path or settings.db_path)
    if not hasattr(_local, "connections"):
        _local.connections = {}
    if target_path not in _local.connections or target_path == ":memory:":
        if target_path != ":memory:":
            Path(target_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(target_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        _local.connections[target_path] = conn
    return _local.connections[target_path]


@contextmanager
def get_db(db_path: str | Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database operations within a transaction."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db(db_path: str | Path | None = None) -> None:
    """Initialize database tables and indexes."""
    with get_db(db_path) as conn:
        conn.executescript(CREATE_TABLES_SQL)


def seed_demo_data(db_path: str | Path | None = None) -> None:
    """Seed initial 7 ISP tenants, exporters, and default users."""
    init_db(db_path)
    now = datetime.now(UTC).isoformat()

    from .auth.service import hash_password
    demo_pass_hash = hash_password("FcsDemo2026!", salt="fcs_dev_salt")

    # 7 Simulated ISP Tenants
    tenants = [
        ("rural-isp-alpha", "Alpha Rural Telecom & Broadband", "ACTIVE", "ap-south-1", 10000),
        ("rural-isp-bravo", "Bravo Regional Wireless Co-op", "ACTIVE", "ap-south-1", 8000),
        ("rural-isp-charlie", "Charlie Municipal Fiber Network", "ACTIVE", "ap-south-1", 15000),
        ("rural-isp-delta", "Delta Valley Community Internet", "ACTIVE", "ap-south-1", 5000),
        ("rural-isp-echo", "Echo Enterprise Transit Provider", "ACTIVE", "ap-south-1", 20000),
        ("rural-isp-foxtrot", "Foxtrot Agricultural & Education Net", "ACTIVE", "ap-south-1", 6000),
        ("rural-isp-golf", "Golf Highlands Wireless Link", "ACTIVE", "ap-south-1", 4000),
    ]

    # Exporters for tenants
    exporters = [
        ("exp-alpha-core1", "rural-isp-alpha", "10.10.1.1", 1, 1, "HEALTHY", now),
        ("exp-alpha-edge2", "rural-isp-alpha", "10.10.1.2", 2, 1, "HEALTHY", now),
        ("exp-bravo-wisp1", "rural-isp-bravo", "10.20.1.1", 1, 1, "HEALTHY", now),
        ("exp-charlie-gw1", "rural-isp-charlie", "10.30.1.1", 1, 1, "HEALTHY", now),
        ("exp-delta-core1", "rural-isp-delta", "10.40.1.1", 1, 1, "HEALTHY", now),
        ("exp-echo-transit", "rural-isp-echo", "10.50.1.1", 1, 1, "HEALTHY", now),
        ("exp-foxtrot-edu", "rural-isp-foxtrot", "10.60.1.1", 1, 1, "HEALTHY", now),
        ("exp-golf-tower1", "rural-isp-golf", "10.70.1.1", 1, 1, "HEALTHY", now),
    ]

    # Users across roles and tenants
    users = [
        ("user_admin_alpha", "admin_alpha", demo_pass_hash, "rural-isp-alpha", "TENANT_ADMIN", "Alpha SOC Administrator"),
        ("user_analyst_alpha", "analyst_alpha", demo_pass_hash, "rural-isp-alpha", "SECURITY_ANALYST", "Alpha Tier-1 Analyst"),
        ("user_responder_alpha", "responder_alpha", demo_pass_hash, "rural-isp-alpha", "SECURITY_RESPONDER", "Alpha Incident Responder"),
        ("user_viewer_alpha", "viewer_alpha", demo_pass_hash, "rural-isp-alpha", "READ_ONLY", "Alpha Auditor / Read-Only"),
        ("user_analyst_bravo", "analyst_bravo", demo_pass_hash, "rural-isp-bravo", "SECURITY_ANALYST", "Bravo Security Analyst"),
        ("user_responder_bravo", "responder_bravo", demo_pass_hash, "rural-isp-bravo", "SECURITY_RESPONDER", "Bravo Incident Responder"),
        ("user_platform_admin", "platform_admin", demo_pass_hash, None, "PLATFORM_ADMIN", "Global Platform Operator"),
    ]

    with get_db(db_path) as conn:
        for t in tenants:
            conn.execute(
                "INSERT OR REPLACE INTO tenants (tenant_id, name, status, region, max_events_per_sec, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (*t, now),
            )
        for e in exporters:
            conn.execute(
                "INSERT OR REPLACE INTO exporters (exporter_id, tenant_id, ip_address, observation_domain_id, sample_rate, status, last_seen_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (*e, now),
            )
        for u in users:
            conn.execute(
                "INSERT OR REPLACE INTO users (user_id, username, password_hash, tenant_id, role, full_name, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (*u, now),
            )

        # Seed initial authorized DetectionBundle
        import json
        bundle_hashes = {
            "lightgbm_deployable_subset": "f776a93db005a242c329d183a04f83899aaaaf72972ed884525bacda368a8f58",
            "isolationforest_anomaly_tenant": "93efc8df38b5b2e942d4762c9ac99cf02752cd9edeb7fe709c356e98d9ca1b8f",
            "lightgbm_ddos_specialist": "a43bbb2c9930e43b9375901ad1a9c033f2b14c5168a06447f7ee2a6eb16fc0dd",
            "lightgbm_scanning_specialist": "db34b856925c81762b348786ab0834e03d7b3a67385cd0d9850b5843d83c656f",
        }
        conn.execute(
            """
            INSERT OR REPLACE INTO detection_bundles (
                bundle_id, version, general_model_id, anomaly_model_id,
                specialist_model_ids_json, model_hashes_json, bundle_digest,
                authorized_by, status, created_at, activated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "fcs-hmd-bundle-v1",
                "1.2.0",
                "lightgbm_deployable_subset",
                "isolationforest_anomaly_tenant",
                json.dumps(["lightgbm_ddos_specialist", "lightgbm_scanning_specialist"]),
                json.dumps(bundle_hashes),
                "2bd8454c761cc75af262f25b11fa6031385c22649e6ad51c7e1eb2a88a40e493",
                "security_admin",
                "ACTIVE",
                now,
                now,
            ),
        )


def reset_db(db_path: str | Path | None = None) -> None:
    """Safely wipe and re-seed the development demonstration database."""
    target_path = str(db_path or settings.db_path)
    # Protection guard: Do not allow reset if running in production mode
    if settings.environment == "production":
        raise RuntimeError("CRITICAL: reset_db is strictly prohibited in production environment!")

    tables = [
        "simulated_firewall_rules",
        "action_journal",
        "recommendations",
        "incident_history",
        "incidents",
        "model_scores",
        "routing_decisions",
        "detection_bundles",
        "detection_scores",
        "feature_windows",
        "flow_events",
        "notification_outbox",
        "audit_events",
        "exporters",
        "users",
        "tenants",
        "service_health",
    ]
    with get_db(target_path) as conn:
        for t in tables:
            conn.execute(f"DROP TABLE IF EXISTS {t};")
    seed_demo_data(target_path)


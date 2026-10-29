"""Threat detection and ML inference coordination service powered by FCS-HMD."""

import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Dynamically ensure workspace root and ml_training/src are in sys.path
_ROOT_DIR = Path(__file__).resolve().parents[5]
_ML_SRC = _ROOT_DIR / "services" / "ml_training" / "src"
for _p in [str(_ROOT_DIR), str(_ML_SRC)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from fcs_ml.hmd.bundle import DetectionBundle
    from fcs_ml.hmd.executor import HierarchicalDetectionEngine
    from fcs_ml.registry.registry import CandidateModelRegistry
except ImportError:
    DetectionBundle = None  # type: ignore[assignment, misc]
    HierarchicalDetectionEngine = None  # type: ignore[assignment, misc]
    CandidateModelRegistry = None  # type: ignore[assignment, misc]

from ..config import settings  # noqa: E402
from ..database import get_db  # noqa: E402
from .rules import ThreatDetectionRules  # noqa: E402

logger = logging.getLogger(__name__)


class DetectionService:
    """
    Coordinates FCS-HMD Hierarchical Multi-Model Intrusion Detection,
    deterministic rules, conditional specialist routing, and evidence fusion.
    """

    def __init__(self, model_registry_dir: str | None = None) -> None:
        self.registry_dir = model_registry_dir or settings.model_registry_dir
        self.default_model_id = settings.default_model_id
        self._hmd_engine: Any = None
        self._model_status: str = "READY"
        self._last_error: str | None = None

        abs_reg_dir = Path(self.registry_dir)
        if not abs_reg_dir.is_absolute():
            abs_reg_dir = _ROOT_DIR / self.registry_dir

        if HierarchicalDetectionEngine is None:
            self._model_status = "MODEL_NOT_AVAILABLE"
            self._last_error = "fcs_ml.hmd module not imported"
            return

        if not abs_reg_dir.exists() or not any(abs_reg_dir.glob("*.json")):
            self._model_status = "MODEL_NOT_AVAILABLE"
            self._last_error = f"Model registry directory missing or empty: {abs_reg_dir}"
            return

        try:
            self._hmd_engine = HierarchicalDetectionEngine(
                registry_dir=abs_reg_dir,
                default_bundle_id="fcs-hmd-bundle-v1",
            )
            self._model_status = "READY"
        except Exception as e:
            logger.warning(f"HierarchicalDetectionEngine initialization failed: {e}. Falling back to RULES_ONLY.")
            self._model_status = "MODEL_NOT_AVAILABLE"
            self._last_error = str(e)

    def get_model_health(self) -> dict[str, Any]:
        """Return runtime health status and metadata for active hierarchical ensemble."""
        active_bundle = self._hmd_engine.get_active_bundle() if self._hmd_engine else None
        return {
            "model_id": self.default_model_id,
            "status": self._model_status,
            "registry_dir": str(self.registry_dir),
            "last_error": self._last_error,
            "deployable_features_count": 14,
            "fallback_mode": "RULES_ONLY" if self._model_status != "READY" else "HIERARCHICAL_MULTI_MODEL",
            "active_bundle_id": active_bundle.bundle_id if active_bundle else "none",
            "bundle_digest": active_bundle.bundle_digest if active_bundle else "none",
            "general_model": active_bundle.general_model_id if active_bundle else self.default_model_id,
            "anomaly_model": active_bundle.anomaly_model_id if active_bundle else "none",
            "specialist_models": active_bundle.specialist_model_ids if active_bundle else [],
            "zero_cost_runtime": "Local CPU Only (₹0.00 Budget)",
            "security_invariant": "network_action_executed = False",
        }

    def get_active_bundle(self) -> dict[str, Any]:
        """Return the active DetectionBundle details."""
        if not self._hmd_engine or not self._hmd_engine.get_active_bundle():
            return {"status": "NO_ACTIVE_BUNDLE", "bundle_id": "none"}
        b = self._hmd_engine.get_active_bundle()
        return b.model_dump()

    def activate_bundle(self, bundle_dict: dict[str, Any], actor_id: str, role: str) -> dict[str, Any]:
        """Authorized activation of a detection bundle."""
        if not self._hmd_engine:
            raise RuntimeError("Hierarchical detection engine is unavailable.")
        bundle = DetectionBundle(**bundle_dict).seal()
        res = self._hmd_engine.activate_bundle(bundle, authorized_by=actor_id, role=role)
        if res.get("success"):
            now = datetime.now(UTC).isoformat()
            with get_db() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO detection_bundles (
                        bundle_id, version, general_model_id, anomaly_model_id,
                        specialist_model_ids_json, model_hashes_json, bundle_digest,
                        authorized_by, status, created_at, activated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        bundle.bundle_id,
                        bundle.version,
                        bundle.general_model_id,
                        bundle.anomaly_model_id,
                        json.dumps(bundle.specialist_model_ids),
                        json.dumps(bundle.model_hashes),
                        bundle.bundle_digest,
                        actor_id,
                        "ACTIVE",
                        bundle.created_at,
                        now,
                    ),
                )
        return res

    def rollback_bundle(self, actor_id: str, role: str) -> dict[str, Any]:
        """Authorized rollback to previous detection bundle."""
        if not self._hmd_engine:
            raise RuntimeError("Hierarchical detection engine is unavailable.")
        res = self._hmd_engine.rollback_bundle(authorized_by=actor_id, role=role)
        return res

    def get_routing_decisions(self, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve recent routing decisions from database."""
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM routing_decisions
                WHERE tenant_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (tenant_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_isp_anomaly_status(self, tenant_id: str) -> dict[str, Any]:
        """Retrieve anomaly detection baseline status for a given rural ISP tenant."""
        with get_db() as conn:
            cnt = conn.execute(
                "SELECT COUNT(*) as c FROM feature_windows WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()["c"]

        return {
            "tenant_id": tenant_id,
            "baseline_status": "CALIBRATED" if cnt > 0 else "WARMUP",
            "isolation_boundary": "STRICT_PER_TENANT",
            "anomaly_model_family": "IsolationForest",
            "contamination_floor": 0.05,
            "monitored_windows_count": cnt,
            "cross_tenant_access": "BLOCKED",
        }

    def list_registered_models(self) -> list[dict[str, Any]]:
        """List all candidate and specialist models from the candidate registry."""
        if not self._hmd_engine:
            return []
        return self._hmd_engine.registry.list_models()

    def analyze_window(
        self,
        window_data: dict[str, Any],
        flow_event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate feature window and flow event using FCS-HMD Hierarchical Multi-Model Engine.
        Combines Level 1 detectors, conditional specialist routing, rules, and evidence fusion.
        """
        tenant_id = window_data["tenant_id"]
        score_id = f"score_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC).isoformat()

        # 1. Evaluate Rule Engine
        rule_matches = ThreatDetectionRules.evaluate(window_data, flow_event)

        # 2. Evaluate FCS-HMD Hierarchical Detection Engine
        if self._hmd_engine and self._model_status == "READY":
            try:
                evidence = self._hmd_engine.evaluate_window(
                    window_data=window_data,
                    flow_event=flow_event,
                    rule_matches=rule_matches,
                )
                composite_risk = evidence.composite_risk
                severity = evidence.severity
                attack_category = evidence.attack_category
                is_threat = evidence.is_threat
                gen_score = evidence.general_score
                routing_dec = evidence.routing_decision
                multi_model_evidence = {
                    "general_score": evidence.general_score.model_dump(),
                    "anomaly_score": evidence.anomaly_score.model_dump(),
                    "specialist_scores": [s.model_dump() for s in evidence.specialist_scores],
                    "routing_decision": evidence.routing_decision.model_dump(),
                    "fusion_method": evidence.fusion_method,
                    "weights_applied": evidence.weights_applied,
                    "uncertainty_flag": evidence.uncertainty_flag,
                    "reason_codes": evidence.reason_codes,
                    "total_latency_us": evidence.total_inference_latency_us,
                }
                inference_status = gen_score.status.value
                ml_score = gen_score.raw_score
                calibrated_prob = gen_score.calibrated_probability
                threshold_applied = gen_score.threshold_applied
                prediction = gen_score.prediction
                predicted_label = gen_score.predicted_label
                is_uncertain = gen_score.is_uncertain
                latency_us = evidence.total_inference_latency_us

                # Persist routing decision
                with get_db() as conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO routing_decisions (
                            decision_id, tenant_id, window_id, level1_general_score,
                            level1_anomaly_score, should_route, routed_models_json,
                            bypassed_models_json, trigger_reasons_json, routing_latency_us, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            routing_dec.decision_id,
                            tenant_id,
                            window_data.get("window_id"),
                            routing_dec.level1_general_score,
                            routing_dec.level1_anomaly_score,
                            1 if routing_dec.should_route_specialists else 0,
                            json.dumps(routing_dec.routed_models),
                            json.dumps(routing_dec.bypassed_models),
                            json.dumps(routing_dec.trigger_reasons),
                            routing_dec.routing_latency_us,
                            now,
                        ),
                    )

                    # Persist individual model scores
                    for s in [evidence.general_score, evidence.anomaly_score] + evidence.specialist_scores:
                        s_id = f"mscore_{uuid.uuid4().hex[:10]}"
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO model_scores (
                                score_id, tenant_id, window_id, model_id, model_type,
                                version, raw_score, calibrated_probability, threshold_applied,
                                prediction, predicted_label, is_uncertain, status,
                                latency_microseconds, reason_codes_json, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                s_id,
                                tenant_id,
                                window_data.get("window_id"),
                                s.model_id,
                                s.model_type.value if hasattr(s.model_type, "value") else str(s.model_type),
                                s.version,
                                s.raw_score,
                                s.calibrated_probability,
                                s.threshold_applied,
                                s.prediction,
                                s.predicted_label,
                                1 if s.is_uncertain else 0,
                                s.status.value if hasattr(s.status, "value") else str(s.status),
                                s.latency_microseconds,
                                json.dumps(s.reason_codes),
                                now,
                            ),
                        )

            except Exception as e:
                logger.error(f"FCS-HMD inference failed: {e}. Falling back to RULES_ONLY.")
                composite_risk = 0.0
                for r in rule_matches:
                    sev = r.get("severity", "LOW")
                    if sev == "CRITICAL":
                        composite_risk = max(composite_risk, 0.95)
                    elif sev == "HIGH":
                        composite_risk = max(composite_risk, 0.85)
                    elif sev == "MEDIUM":
                        composite_risk = max(composite_risk, 0.65)
                    elif sev == "LOW":
                        composite_risk = max(composite_risk, 0.40)
                severity = "CRITICAL" if composite_risk >= 0.85 else ("HIGH" if composite_risk >= 0.70 else ("MEDIUM" if composite_risk >= 0.50 else "LOW"))
                attack_category = rule_matches[0]["attack_category"] if rule_matches else "Benign"
                is_threat = composite_risk >= 0.40
                inference_status = "FALLBACK_RULES_ONLY"
                ml_score = 0.0
                calibrated_prob = 0.0
                threshold_applied = 0.5
                prediction = 0
                predicted_label = "NOT_SCORED"
                is_uncertain = False
                latency_us = 0.0
                multi_model_evidence = {"fallback": "RULES_ONLY", "error": str(e)}
        else:
            # RULES_ONLY Mode
            composite_risk = 0.0
            for r in rule_matches:
                sev = r.get("severity", "LOW")
                if sev == "CRITICAL":
                    composite_risk = max(composite_risk, 0.95)
                elif sev == "HIGH":
                    composite_risk = max(composite_risk, 0.85)
                elif sev == "MEDIUM":
                    composite_risk = max(composite_risk, 0.65)
                elif sev == "LOW":
                    composite_risk = max(composite_risk, 0.40)
            severity = "CRITICAL" if composite_risk >= 0.85 else ("HIGH" if composite_risk >= 0.70 else ("MEDIUM" if composite_risk >= 0.50 else "LOW"))
            attack_category = rule_matches[0]["attack_category"] if rule_matches else "Benign"
            is_threat = composite_risk >= 0.40
            inference_status = "RULES_ONLY"
            ml_score = 0.0
            calibrated_prob = 0.0
            threshold_applied = 0.5
            prediction = 0
            predicted_label = "NOT_SCORED"
            is_uncertain = False
            latency_us = 0.0
            multi_model_evidence = {"mode": "RULES_ONLY"}

        # Persist score record in database (for Phase 4 backward compatibility)
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO detection_scores (
                    score_id, tenant_id, window_id, model_id, model_version,
                    raw_score, calibrated_probability, threshold_applied,
                    prediction, predicted_label, is_uncertain, status,
                    latency_microseconds, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    score_id,
                    tenant_id,
                    window_data.get("window_id"),
                    self.default_model_id,
                    "1.2.0",
                    ml_score,
                    calibrated_prob,
                    threshold_applied,
                    prediction,
                    predicted_label,
                    1 if is_uncertain else 0,
                    inference_status,
                    latency_us,
                    now,
                ),
            )

        return {
            "score_id": score_id,
            "tenant_id": tenant_id,
            "severity": severity,
            "risk_score": composite_risk,
            "attack_category": attack_category,
            "is_threat": is_threat,
            "rule_matches": rule_matches,
            "ml_inference": {
                "model_id": self.default_model_id,
                "status": inference_status,
                "raw_score": ml_score,
                "calibrated_probability": calibrated_prob,
                "threshold_applied": threshold_applied,
                "is_uncertain": is_uncertain,
                "latency_microseconds": latency_us,
                "network_action_executed": False,  # Always FALSE
            },
            "multi_model_evidence": multi_model_evidence,
        }

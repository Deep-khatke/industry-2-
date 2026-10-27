"""HierarchicalDetectionEngine: Orchestrates routing, specialist execution, timeouts, and fusion."""

import json
import logging
import time
from pathlib import Path
from typing import Any

import numpy as np

from fcs_ml.registry.manifest import ModelManifest
from fcs_ml.registry.registry import CandidateModelRegistry
from packages.contracts.model_score import ModelScore, ModelType, ScoringStatus

from .bundle import BundleValidator, DetectionBundle
from .fusion import CompositeThreatEvidence, EvidenceFusionEngine
from .router import ConditionalModelRouter

logger = logging.getLogger(__name__)


class HierarchicalDetectionEngine:
    """
    FCS-HMD Hierarchical Multi-Model Intrusion Detection Engine.
    Executes Level 1 general and tenant anomaly models, conditionally routes
    specialists under latency budgets, and performs deterministic evidence fusion.
    """

    def __init__(
        self,
        registry_dir: Path | str = "artifacts/candidate-models",
        default_bundle_id: str = "fcs-hmd-bundle-v1",
        specialist_timeout_us: float = 100_000.0,  # 100ms per model budget
        max_total_latency_us: float = 250_000.0,
    ) -> None:
        self.registry = CandidateModelRegistry(registry_dir=registry_dir)
        self.specialist_timeout_us = specialist_timeout_us
        self.max_total_latency_us = max_total_latency_us
        self.router = ConditionalModelRouter()
        self.fusion_engine = EvidenceFusionEngine()

        self._cached_models: dict[str, tuple[Any, ModelManifest]] = {}
        self._tenant_anomaly_models: dict[str, tuple[Any, ModelManifest]] = {}
        self._active_bundle: DetectionBundle | None = None
        self._previous_bundle: DetectionBundle | None = None
        self._bundle_history: list[DetectionBundle] = []
        self._engine_status: str = "INITIALIZING"

        # Load Phase 2 preprocessor scaling parameters if present
        self._preprocessor_state: dict[str, Any] | None = None
        for cand_prep in [Path("data/processed/preprocessor_state.json"), Path(__file__).resolve().parents[5] / "data" / "processed" / "preprocessor_state.json"]:
            if cand_prep.exists():
                try:
                    self._preprocessor_state = json.loads(cand_prep.read_text(encoding="utf-8"))
                    break
                except Exception:
                    pass

        # Initialize default active bundle
        self._bootstrap_default_bundle(default_bundle_id)

    def _bootstrap_default_bundle(self, bundle_id: str) -> None:
        """Initialize and validate the default deployment bundle."""
        bundle = DetectionBundle(
            bundle_id=bundle_id,
            version="1.2.0",
            general_model_id="lightgbm_deployable_subset",
            anomaly_model_id="isolationforest_anomaly_tenant",
            specialist_model_ids=["lightgbm_ddos_specialist", "lightgbm_scanning_specialist"],
            authorized_by="system_bootstrap",
            status="ACTIVE",
        ).seal()

        val = BundleValidator.validate(bundle, self.registry)
        if val["is_valid"]:
            self._active_bundle = bundle
            self._bundle_history.append(bundle)
            self._engine_status = "READY"
        else:
            logger.warning(f"Default bundle '{bundle_id}' validation encountered missing models: {val['errors']}. Operating in DEGRADED/ADAPTIVE mode.")
            self._active_bundle = bundle
            self._engine_status = "DEGRADED"

    def get_model(self, model_id: str) -> tuple[Any, ModelManifest] | None:
        """Retrieve model and manifest from cache or registry."""
        if model_id in self._cached_models:
            return self._cached_models[model_id]
        try:
            model, manifest = self.registry.load_model(model_id)
            self._cached_models[model_id] = (model, manifest)
            return model, manifest
        except Exception as e:
            logger.error(f"Failed to load model '{model_id}': {e}")
            return None

    def register_tenant_anomaly_model(
        self,
        tenant_id: str,
        model: Any,
        manifest: ModelManifest,
    ) -> None:
        """Register a tenancy-isolated anomaly detector for a specific rural ISP."""
        self._tenant_anomaly_models[tenant_id] = (model, manifest)

    def get_active_bundle(self) -> DetectionBundle | None:
        return self._active_bundle

    def get_status(self) -> str:
        """Return current operational status of the detection engine."""
        return self._engine_status

    def activate_bundle(
        self,
        bundle: DetectionBundle,
        authorized_by: str,
        role: str,
    ) -> dict[str, Any]:
        """Authorized activation of a detection bundle."""
        if role not in ("PLATFORM_ADMIN", "TENANT_ADMIN"):
            raise PermissionError(f"Role '{role}' is not authorized to activate detection bundles.")

        val = BundleValidator.validate(bundle, self.registry)
        if not val["is_valid"]:
            return {
                "success": False,
                "message": f"Bundle validation failed: {', '.join(val['errors'])}",
                "bundle_id": bundle.bundle_id,
            }

        self._previous_bundle = self._active_bundle
        bundle.status = "ACTIVE"
        bundle.authorized_by = authorized_by
        bundle.activated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._active_bundle = bundle
        self._bundle_history.append(bundle)
        self._engine_status = "READY"

        return {
            "success": True,
            "message": f"Bundle '{bundle.bundle_id}' successfully activated by {authorized_by}.",
            "bundle_digest": bundle.bundle_digest,
        }

    def rollback_bundle(self, authorized_by: str, role: str) -> dict[str, Any]:
        """Rollback to the previous active detection bundle."""
        if role not in ("PLATFORM_ADMIN", "TENANT_ADMIN"):
            raise PermissionError(f"Role '{role}' is not authorized to rollback detection bundles.")

        if not self._previous_bundle:
            return {
                "success": False,
                "message": "No previous detection bundle available for rollback.",
            }

        prev = self._previous_bundle
        val = BundleValidator.validate(prev, self.registry)
        if not val["is_valid"]:
            return {
                "success": False,
                "message": f"Rollback target '{prev.bundle_id}' is invalid: {val['errors']}",
            }

        self._previous_bundle = self._active_bundle
        if self._previous_bundle:
            self._previous_bundle.status = "ROLLED_BACK"

        prev.status = "ACTIVE"
        prev.authorized_by = authorized_by
        self._active_bundle = prev
        self._bundle_history.append(prev)

        return {
            "success": True,
            "message": f"Successfully rolled back to bundle '{prev.bundle_id}'.",
            "active_bundle_id": prev.bundle_id,
        }

    def _execute_model_score(
        self,
        model_id: str,
        model_type: ModelType,
        features: dict[str, Any],
        tenant_id: str,
        override_model: Any = None,
        override_manifest: ModelManifest = None,
    ) -> ModelScore:
        """Safely score a single model with latency measurement, schema validation, and timeouts."""
        start_t = time.perf_counter()

        if override_model and override_manifest:
            model, manifest = override_model, override_manifest
        else:
            loaded = self.get_model(model_id)
            if loaded is None:
                return ModelScore.missing(model_id, model_type, tenant_context=tenant_id)
            model, manifest = loaded

        # Extract numerical feature vector matching manifest
        feat_names = manifest.feature_names
        vector: list[float] = []
        for fn in feat_names:
            val = features.get(fn, 0.0)
            try:
                num_v = float(val) if val is not None else 0.0
                if np.isnan(num_v) or np.isinf(num_v):
                    num_v = 0.0
            except (ValueError, TypeError):
                num_v = 0.0

            # Apply training-only robust scaler centers and dispersions for tabular models
            if self._preprocessor_state:
                centers = self._preprocessor_state.get("scale_center", {})
                dispersions = self._preprocessor_state.get("scale_dispersion", {})
                if fn in centers and fn in dispersions:
                    num_v = (num_v - centers[fn]) / dispersions[fn]

            vector.append(num_v)

        X = np.array([vector], dtype=np.float32)

        try:
            # Check timeout before execution
            elapsed_us = (time.perf_counter() - start_t) * 1_000_000.0
            if elapsed_us > self.specialist_timeout_us:
                return ModelScore.timeout(model_id, model_type, self.specialist_timeout_us, tenant_id)

            proba = model.predict_proba(X)
            latency_us = (time.perf_counter() - start_t) * 1_000_000.0

            if proba.shape[1] > 1:
                raw_score = float(proba[0, 1])
            else:
                raw_score = float(proba[0, 0])

            calibrated_prob = float(np.clip(raw_score, 0.0, 1.0))
            threshold = float(manifest.validation_threshold)
            pred = 1 if calibrated_prob >= threshold else 0

            # Derive semantic label
            if pred == 1:
                if model_type == ModelType.DDOS_SPECIALIST:
                    label = "DDoS"
                elif model_type == ModelType.SCANNING_SPECIALIST:
                    label = "PortScan"
                elif model_type == ModelType.ANOMALY_DETECTOR:
                    label = "Traffic Anomaly"
                else:
                    label = "Attack"
            else:
                label = "Benign"

            # Check uncertainty margin (within 5% of threshold)
            is_uncertain = abs(calibrated_prob - threshold) < 0.05
            status = ScoringStatus.ABSTAIN if is_uncertain else ScoringStatus.SCORED

            return ModelScore(
                model_id=manifest.model_id,
                model_type=model_type,
                version=manifest.version,
                raw_score=raw_score,
                calibrated_probability=calibrated_prob,
                confidence=1.0 - (abs(calibrated_prob - 0.5) * 0.2 if is_uncertain else 0.0),
                threshold_applied=threshold,
                prediction=pred,
                predicted_label=label,
                is_uncertain=is_uncertain,
                status=status,
                latency_microseconds=latency_us,
                features_used=feat_names,
                tenant_context=tenant_id,
                network_action_executed=False,
            )
        except Exception as e:
            logger.error(f"Inference failure for model '{model_id}': {e}")
            return ModelScore(
                model_id=model_id,
                model_type=model_type,
                raw_score=-1.0,
                calibrated_probability=0.0,
                confidence=0.0,
                threshold_applied=0.5,
                prediction=-1,
                predicted_label="ERROR",
                is_uncertain=True,
                status=ScoringStatus.ERROR,
                latency_microseconds=(time.perf_counter() - start_t) * 1_000_000.0,
                reason_codes=[f"ERROR: {e}"],
                tenant_context=tenant_id,
                network_action_executed=False,
            )

    def evaluate_window(
        self,
        window_data: dict[str, Any],
        flow_event: dict[str, Any] | None = None,
        rule_matches: list[dict[str, Any]] | None = None,
    ) -> CompositeThreatEvidence:
        """
        End-to-end evaluation of a 30s feature window through FCS-HMD:
        Level 1 (General + ISP Anomaly) -> Router -> Specialists -> Fusion.
        """
        total_start_t = time.perf_counter()
        tenant_id = window_data.get("tenant_id", "rural-isp-alpha")
        window_id = window_data.get("window_id")
        features = window_data.get("feature_vector", {})
        flow_count = window_data.get("flow_count", 1)
        rules = rule_matches or []

        bundle = self._active_bundle
        general_model_id = bundle.general_model_id if bundle else "lightgbm_deployable_subset"
        anomaly_model_id = bundle.anomaly_model_id if bundle else "isolationforest_anomaly_tenant"

        # 1. Level 1: General Threat Detector
        general_score = self._execute_model_score(
            model_id=general_model_id,
            model_type=ModelType.GENERAL_DETECTOR,
            features=features,
            tenant_id=tenant_id,
        )

        # 2. Level 1: ISP Anomaly Detector (checks for tenant-isolated baseline)
        if tenant_id in self._tenant_anomaly_models:
            t_model, t_manifest = self._tenant_anomaly_models[tenant_id]
            anomaly_score = self._execute_model_score(
                model_id=f"{anomaly_model_id}_{tenant_id}",
                model_type=ModelType.ANOMALY_DETECTOR,
                features=features,
                tenant_id=tenant_id,
                override_model=t_model,
                override_manifest=t_manifest,
            )
        else:
            anomaly_score = self._execute_model_score(
                model_id=anomaly_model_id,
                model_type=ModelType.ANOMALY_DETECTOR,
                features=features,
                tenant_id=tenant_id,
            )

        # 3. Conditional Model Router
        routing_decision = self.router.route(
            features=features,
            general_score=general_score,
            anomaly_score=anomaly_score,
            flow_event=flow_event,
            flow_count=flow_count,
            tenant_id=tenant_id,
            window_id=window_id,
        )

        # 4. Execute routed specialists under timeout budgets
        specialist_scores: list[ModelScore] = []

        if routing_decision.should_route_specialists:
            for spec_name in routing_decision.routed_models:
                # Map router name to bundle model_id
                if spec_name == "ddos_specialist":
                    model_id = "lightgbm_ddos_specialist"
                    m_type = ModelType.DDOS_SPECIALIST
                elif spec_name == "scanning_specialist":
                    model_id = "lightgbm_scanning_specialist"
                    m_type = ModelType.SCANNING_SPECIALIST
                elif spec_name == "botnet_specialist":
                    model_id = "lightgbm_botnet_specialist"
                    m_type = ModelType.BOTNET_SPECIALIST
                else:
                    model_id = spec_name
                    m_type = ModelType.DDOS_SPECIALIST

                score = self._execute_model_score(
                    model_id=model_id,
                    model_type=m_type,
                    features=features,
                    tenant_id=tenant_id,
                )
                specialist_scores.append(score)

        # Record bypassed specialists
        for bypassed in routing_decision.bypassed_models:
            if bypassed == "ddos_specialist":
                m_type = ModelType.DDOS_SPECIALIST
                m_id = "lightgbm_ddos_specialist"
            elif bypassed == "scanning_specialist":
                m_type = ModelType.SCANNING_SPECIALIST
                m_id = "lightgbm_scanning_specialist"
            elif bypassed == "botnet_specialist":
                m_type = ModelType.BOTNET_SPECIALIST
                m_id = "lightgbm_botnet_specialist"
            else:
                m_type = ModelType.DDOS_SPECIALIST
                m_id = bypassed

            specialist_scores.append(
                ModelScore.bypassed(
                    model_id=m_id,
                    model_type=m_type,
                    reason="Not routed by conditional policy",
                    tenant_context=tenant_id,
                )
            )

        total_latency_us = (time.perf_counter() - total_start_t) * 1_000_000.0

        # 5. Deterministic Evidence Fusion
        fused = self.fusion_engine.fuse(
            general_score=general_score,
            anomaly_score=anomaly_score,
            specialist_scores=specialist_scores,
            rule_matches=rules,
            routing_decision=routing_decision,
            total_latency_us=total_latency_us,
        )

        return fused

    def score_flow(
        self,
        flow_dict: dict[str, Any],
        tenant_id: str = "rural-isp-alpha",
        window_id: str | None = None,
        rule_matches: list[dict[str, Any]] | None = None,
    ) -> CompositeThreatEvidence:
        """Convenience method to score an individual flow vector."""
        window_data = {
            "tenant_id": tenant_id,
            "window_id": window_id or f"flow_{int(time.time() * 1000)}",
            "feature_vector": flow_dict,
            "flow_count": 1,
        }
        return self.evaluate_window(window_data=window_data, rule_matches=rule_matches)

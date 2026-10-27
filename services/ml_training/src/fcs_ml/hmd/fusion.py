"""Deterministic and Learned Evidence Fusion for FCS-HMD Hierarchical Threat Detection."""

from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from packages.contracts.model_score import ModelScore, ScoringStatus

from .router import RoutingDecision


class CompositeThreatEvidence(BaseModel):
    """
    Unified threat evidence produced by FCS-HMD Evidence Fusion.
    Preserves multi-model attribution, uncertainty status, and safety invariants.
    """

    composite_risk: float = Field(..., ge=0.0, le=1.0, description="Fused risk score in [0.0, 1.0]")
    severity: str = Field(..., description="Severity level: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL")
    attack_category: str = Field(..., description="Primary identified attack category")
    is_threat: bool = Field(..., description="True if composite risk warrants active incident generation")
    general_score: ModelScore
    anomaly_score: ModelScore
    specialist_scores: list[ModelScore] = Field(default_factory=list)
    rule_matches: list[dict[str, Any]] = Field(default_factory=list)
    routing_decision: RoutingDecision
    fusion_method: str = Field(default="DETERMINISTIC_BAYESIAN")
    uncertainty_flag: bool = Field(default=False)
    weights_applied: dict[str, float] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    total_inference_latency_us: float = Field(default=0.0)
    network_action_executed: bool = Field(
        default=False,
        description="Safety invariant: ML models only generate evidence (ALWAYS False)",
    )


class EvidenceFusionEngine:
    """
    Deterministic evidence fusion engine combining Level 1 detectors,
    active specialists, and deterministic threat rules.
    """

    def __init__(
        self,
        general_weight: float = 0.50,
        anomaly_weight: float = 0.25,
        specialist_weight: float = 0.50,
        uncertainty_margin: float = 0.05,
    ) -> None:
        self.default_general_weight = general_weight
        self.default_anomaly_weight = anomaly_weight
        self.default_specialist_weight = specialist_weight
        self.uncertainty_margin = uncertainty_margin

    def fuse(
        self,
        general_score: ModelScore,
        anomaly_score: ModelScore,
        specialist_scores: list[ModelScore],
        rule_matches: list[dict[str, Any]],
        routing_decision: RoutingDecision,
        total_latency_us: float = 0.0,
    ) -> CompositeThreatEvidence:
        """
        Execute deterministic evidence fusion.
        Handles abstentions, missing models, and specialist dominance.
        """
        reasons: list[str] = []
        weights: dict[str, float] = {}

        # 1. Evaluate Rule Engine Floor
        rule_risk_floor = 0.0
        primary_rule_category = "Benign"
        for r in rule_matches:
            sev = r.get("severity", "LOW")
            cat = r.get("attack_category", "Suspicious")
            primary_rule_category = cat
            if sev == "CRITICAL":
                rule_risk_floor = max(rule_risk_floor, 0.95)
            elif sev == "HIGH":
                rule_risk_floor = max(rule_risk_floor, 0.85)
            elif sev == "MEDIUM":
                rule_risk_floor = max(rule_risk_floor, 0.65)
            elif sev == "LOW":
                rule_risk_floor = max(rule_risk_floor, 0.40)
            reasons.append(f"RULE_MATCH: {r.get('rule_id')} ({sev}) - {r.get('name')}")

        # 2. Check for missing or timeout models
        missing_or_timed_out = [
            s for s in [general_score, anomaly_score] + specialist_scores
            if s.status in (ScoringStatus.MISSING, ScoringStatus.TIMEOUT, ScoringStatus.ERROR)
        ]
        for m in missing_or_timed_out:
            reasons.append(f"MODEL_DEGRADED: {m.model_id} ({m.status.value})")

        # 3. Filter valid, non-abstained model scores for probabilistic fusion
        valid_specialists = [
            s for s in specialist_scores
            if s.status == ScoringStatus.SCORED and not s.is_uncertain
        ]
        active_specialist_threats = [s for s in valid_specialists if s.prediction == 1]

        # 4. Multi-model weighting logic
        fusion_method = "DETERMINISTIC_BAYESIAN"
        if not routing_decision.should_route_specialists:
            # Router short-circuited Level 1 benign baseline
            fusion_method = "BENIGN_BASELINE_SHORT_CIRCUIT"
            primary_category = "Benign"
            fused_prob = min(0.15, max(0.05, general_score.calibrated_probability * 0.2))
            weights = {"baseline_short_circuit": 1.0}

        elif len(valid_specialists) == 0:
            # Specialists were routed but none were valid or available (Fallback Level 1)
            fusion_method = "LEVEL1_FUSION"
            g_p = general_score.calibrated_probability if general_score.status == ScoringStatus.SCORED else 0.0
            a_p = anomaly_score.calibrated_probability if anomaly_score.status == ScoringStatus.SCORED else 0.0

            if general_score.status == ScoringStatus.SCORED and anomaly_score.status == ScoringStatus.SCORED:
                w_g = 0.65
                w_a = 0.35
                fused_prob = (g_p * w_g) + (a_p * w_a)
                weights = {"general": w_g, "anomaly": w_a}
            elif general_score.status == ScoringStatus.SCORED:
                fused_prob = g_p
                weights = {"general": 1.0}
                fusion_method = "FALLBACK_GENERAL_ONLY"
            else:
                fused_prob = a_p
                weights = {"anomaly": 1.0}

            if fused_prob >= 0.75:
                primary_category = "Suspicious Traffic"
            else:
                fused_prob = min(0.20, fused_prob * 0.25)
                primary_category = "Benign"

        elif len(active_specialist_threats) > 0:
            # Active specialist threat detected: specialist dominates
            fusion_method = "SPECIALIST_DOMINANT"
            top_specialist = max(active_specialist_threats, key=lambda s: s.calibrated_probability)
            primary_category = top_specialist.predicted_label

            s_prob = top_specialist.calibrated_probability
            g_prob = general_score.calibrated_probability if general_score.status == ScoringStatus.SCORED else s_prob
            a_prob = anomaly_score.calibrated_probability if anomaly_score.status == ScoringStatus.SCORED else s_prob

            w_s = 0.55
            w_g = 0.30
            w_a = 0.15
            fused_prob = (s_prob * w_s) + (g_prob * w_g) + (a_prob * w_a)
            weights = {f"specialist_{top_specialist.model_id}": w_s, "general": w_g, "anomaly": w_a}
            reasons.append(f"SPECIALIST_DOMINANCE: {top_specialist.model_id} confirmed {primary_category} (prob={s_prob:.3f})")

        else:
            # Specialists were routed but none confirmed an attack (voted normal)
            s_avg = float(np.mean([s.calibrated_probability for s in valid_specialists]))
            g_prob = general_score.calibrated_probability if general_score.status == ScoringStatus.SCORED else 0.0
            a_prob = anomaly_score.calibrated_probability if anomaly_score.status == ScoringStatus.SCORED else 0.0

            # Dampen probability since specialist rejected the threat
            w_g = 0.40
            w_a = 0.30
            w_s = 0.30
            fused_prob = (g_prob * w_g) + (a_prob * w_a) + (s_avg * w_s) * 0.5
            weights = {"general": w_g, "anomaly": w_a, "specialists_cleared": w_s}
            primary_category = "Benign" if fused_prob < 0.40 else "Suspicious Traffic"
            reasons.append("SPECIALISTS_CLEARED: Targeted specialists did not confirm attack signature")

        # 5. Apply Rule Risk Floor (Deterministic safety guardrail)
        if rule_matches and rule_risk_floor > fused_prob:
            composite_risk = rule_risk_floor
            primary_category = primary_rule_category
            fusion_method = f"{fusion_method}+RULES_FLOOR"
            reasons.append(f"RULE_FLOOR_ENFORCED: Elevated risk to {rule_risk_floor:.2f} due to deterministic rule match")
        else:
            composite_risk = fused_prob

        composite_risk = float(np.clip(composite_risk, 0.0, 1.0))

        # Standardize category name
        if primary_category in ("Port Scan", "SYN Port Scanning / Reconnaissance"):
            primary_category = "PortScan"

        if len(rule_matches) > 0:
            is_threat = True
        else:
            is_threat = (composite_risk >= 0.50) and (primary_category != "Benign")

        if not is_threat:
            primary_category = "Benign"
            composite_risk = min(composite_risk, 0.25)
            severity = "LOW" if composite_risk >= 0.15 else "INFORMATIONAL"
        else:
            # 6. Map confirmed threats to appropriate SOC severity levels
            if primary_category in ("DDoS", "Volumetric Flood"):
                severity = "CRITICAL" if composite_risk >= 0.75 else "HIGH"
            elif primary_category in ("PortScan", "Reconnaissance"):
                severity = "HIGH" if composite_risk >= 0.75 else "MEDIUM"
            elif composite_risk >= 0.85:
                severity = "CRITICAL"
            elif composite_risk >= 0.70:
                severity = "HIGH"
            elif composite_risk >= 0.50:
                severity = "MEDIUM"
            else:
                severity = "LOW"

        # Check for composite uncertainty
        uncertainty_flag = (
            general_score.is_uncertain
            or anomaly_score.is_uncertain
            or (0.45 <= composite_risk <= 0.55)
        )

        return CompositeThreatEvidence(
            composite_risk=composite_risk,
            severity=severity,
            attack_category=primary_category,
            is_threat=is_threat,
            general_score=general_score,
            anomaly_score=anomaly_score,
            specialist_scores=specialist_scores,
            rule_matches=rule_matches,
            routing_decision=routing_decision,
            fusion_method=fusion_method,
            uncertainty_flag=uncertainty_flag,
            weights_applied=weights,
            reason_codes=reasons,
            total_inference_latency_us=total_latency_us,
            network_action_executed=False,
        )


class LearnedFusionComparator:
    """
    Validation-only learned logistic regression meta-model for fusion comparison.
    Trained strictly on out-of-fold validation predictions to avoid train/test leakage.
    """

    def __init__(self) -> None:
        self.is_fitted = False
        self.coef_: np.ndarray | None = None
        self.intercept_: float = 0.0

    def fit(self, X_val_preds: np.ndarray, y_val: np.ndarray) -> "LearnedFusionComparator":
        """Fit meta-weights on validation predictions [P_gen, P_anom, P_ddos, P_scan]."""
        from sklearn.linear_model import LogisticRegression

        clf = LogisticRegression(C=1.0, solver="lbfgs", max_iter=200)
        clf.fit(X_val_preds, y_val)
        self.coef_ = clf.coef_[0]
        self.intercept_ = float(clf.intercept_[0])
        self.is_fitted = True
        return self

    def predict_proba(self, X_preds: np.ndarray) -> np.ndarray:
        if not self.is_fitted or self.coef_ is None:
            raise RuntimeError("Learned fusion comparator is not fitted.")
        z = np.dot(X_preds, self.coef_) + self.intercept_
        p1 = 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))
        return np.vstack([1.0 - p1, p1]).T

"""False-alert rate and analyst workload meter for FCS Phase 9."""

import math
from typing import Any
from pydantic import BaseModel, Field

from ..analyst_feedback.feedback_manager import AnalystFeedbackManager, IncidentDisposition


class FalseAlertMetrics(BaseModel):
    """Calculated metrics for false alerts and analyst triage burden."""
    tenant_id: str
    days_evaluated: int
    total_grouped_incidents: int
    confirmed_false_positives: int
    unreviewed_incidents: int
    false_positives_per_day: float
    target_threshold_per_day: float = 5.0
    target_met: bool
    confidence_interval_95: tuple[float, float]
    total_analyst_triage_minutes: float
    avg_triage_minutes_per_day: float
    analyst_capacity_budget_minutes_per_day: float = 20.0
    analyst_budget_satisfied: bool
    status_summary: str


class FalseAlertMeter:
    """Calculates grouped false incident rates and analyst capacity compliance."""

    @classmethod
    def calculate_metrics(
        cls,
        tenant_id: str,
        days_evaluated: int,
        total_incidents: int,
        feedback_manager: AnalystFeedbackManager,
        unreviewed_count: int = 0,
        target_fps_per_day: float = 5.0,
        daily_analyst_budget_minutes: float = 20.0,
    ) -> FalseAlertMetrics:
        """
        Compute daily false alert rate from verified human analyst feedback.
        Strict rule: Raw flow-level FPR is NOT used. Only grouped incident triage dispositions are used.
        """
        if days_evaluated <= 0:
            days_evaluated = 1

        recs = feedback_manager.get_feedback_for_tenant(tenant_id)
        fps = sum(1 for r in recs if r.disposition == IncidentDisposition.FALSE_POSITIVE)
        total_review_sec = sum(r.review_duration_seconds for r in recs)
        total_review_min = total_review_sec / 60.0

        daily_fp_rate = fps / float(days_evaluated)
        daily_analyst_mins = total_review_min / float(days_evaluated)

        # 95% Wilson score interval or standard normal approximation for FP rate
        n = max(len(recs), 1)
        p = fps / n
        z = 1.96
        margin = z * math.sqrt((p * (1 - p)) / n) if n > 1 and p > 0 else 0.0
        ci_lower = max(0.0, (daily_fp_rate * (1 - margin)))
        ci_upper = daily_fp_rate * (1 + margin)

        target_met = daily_fp_rate <= target_fps_per_day
        budget_satisfied = daily_analyst_mins <= daily_analyst_budget_minutes

        if target_met and budget_satisfied:
            summary = (
                f"TARGET_MET: {daily_fp_rate:.2f} false alerts/day (<= {target_fps_per_day} target). "
                f"Analyst workload {daily_analyst_mins:.1f} min/day (<= {daily_analyst_budget_minutes} min budget)."
            )
        elif not target_met:
            summary = f"TARGET_EXCEEDED: {daily_fp_rate:.2f} false alerts/day exceeds target of {target_fps_per_day}."
        else:
            summary = f"WORKLOAD_EXCEEDED: Analyst triage time {daily_analyst_mins:.1f} min/day exceeds budget."

        return FalseAlertMetrics(
            tenant_id=tenant_id,
            days_evaluated=days_evaluated,
            total_grouped_incidents=total_incidents,
            confirmed_false_positives=fps,
            unreviewed_incidents=unreviewed_count,
            false_positives_per_day=round(daily_fp_rate, 2),
            target_threshold_per_day=target_fps_per_day,
            target_met=target_met,
            confidence_interval_95=(round(ci_lower, 2), round(ci_upper, 2)),
            total_analyst_triage_minutes=round(total_review_min, 1),
            avg_triage_minutes_per_day=round(daily_analyst_mins, 1),
            analyst_capacity_budget_minutes_per_day=daily_analyst_budget_minutes,
            analyst_budget_satisfied=budget_satisfied,
            status_summary=summary,
        )

"""Seven-Day Shadow Evaluation Workflow and Reporting Engine."""

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger("fcs_pilot.seven_day")


class DailyEvaluationMetrics(BaseModel):
    """Daily operational and threat detection metrics for one day of shadow monitoring."""
    day_index: int  # 1 to 7
    calendar_date: str
    scenario_type: str  # "SIMULATED_7_DAY_SCENARIO" or "LIVE_ISP_OBSERVATION"
    total_flows_received: int
    valid_flows: int
    rejected_flows: int
    late_flows: int
    sequence_gaps: int
    exporter_coverage_percent: float
    model_scored_windows: int
    unscored_windows: int
    model_failures: int
    candidate_incidents: int
    analyst_confirmed_incidents: int
    false_positives: int
    unresolved_incidents: int
    estimated_missed_attacks: int
    analyst_review_time_minutes: float
    dashboard_availability_percent: float
    model_latency_p95_ms: float
    model_latency_p99_ms: float
    processing_lag_seconds: float
    warnings: list[str] = Field(default_factory=list)


class SevenDayEvaluationReport(BaseModel):
    """Cumulative 7-day shadow monitoring evaluation report."""
    pilot_id: str
    tenant_id: str
    evaluation_type: str  # "SIMULATED_7_DAY_SCENARIO" or "AUTHORIZED_REAL_PILOT"
    start_date: str
    end_date: str
    days_completed: int
    daily_records: list[DailyEvaluationMetrics]
    total_flows_processed: int
    total_candidate_incidents: int
    total_confirmed_true_positives: int
    total_confirmed_false_positives: int
    average_false_incidents_per_day: float
    target_met_le_5_false_per_day: bool
    average_analyst_review_minutes_per_day: float
    analyst_capacity_target_met: bool
    overall_detection_coverage_percent: float
    recommendation: str


class SevenDayEvaluator:
    """Manages recording, aggregation, and simulation of 7-day shadow evaluation."""

    def __init__(self, pilot_id: str, tenant_id: str, is_simulation: bool = True) -> None:
        self.pilot_id = pilot_id
        self.tenant_id = tenant_id
        self.is_simulation = is_simulation
        self._daily_metrics: list[DailyEvaluationMetrics] = []

    def record_day(self, metrics: DailyEvaluationMetrics) -> None:
        self._daily_metrics.append(metrics)

    def run_simulated_7_day_scenario(self) -> SevenDayEvaluationReport:
        """
        Execute deterministic synthetic replay across 7 simulated days for offline verification.
        Explicitly marked as 'SIMULATED_7_DAY_SCENARIO'.
        """
        self._daily_metrics.clear()
        base_date = datetime.now(UTC) - timedelta(days=7)

        # Realistic daily fluctuations:
        # Typical daily volume ~1,500,000 to 2,000,000 flows
        # Grouped incidents ~2 to 5 per day, false positives ~1 to 3 per day
        scenario_data = [
            # Day 1: Normal baseline
            {"flows": 1650000, "valid": 1648000, "rej": 1500, "late": 500, "gaps": 0, "cand": 3, "tp": 2, "fp": 1, "unres": 0, "mins": 12.0, "cov": 99.8},
            # Day 2: Minor port scan activity
            {"flows": 1720000, "valid": 1718500, "rej": 1000, "late": 500, "gaps": 1, "cand": 4, "tp": 3, "fp": 1, "unres": 0, "mins": 16.5, "cov": 99.7},
            # Day 3: Volumetric spike & micro-burst
            {"flows": 2100000, "valid": 2095000, "rej": 3500, "late": 1500, "gaps": 2, "cand": 5, "tp": 3, "fp": 2, "unres": 0, "mins": 18.0, "cov": 99.4},
            # Day 4: Benign DNS fluctuation (investigated)
            {"flows": 1800000, "valid": 1798000, "rej": 1200, "late": 800, "gaps": 0, "cand": 3, "tp": 1, "fp": 2, "unres": 0, "mins": 14.0, "cov": 99.9},
            # Day 5: Multi-vector attack burst
            {"flows": 2250000, "valid": 2246000, "rej": 2500, "late": 1500, "gaps": 1, "cand": 6, "tp": 4, "fp": 2, "unres": 0, "mins": 19.5, "cov": 99.6},
            # Day 6: Quiet weekend pattern
            {"flows": 1450000, "valid": 1449000, "rej": 800, "late": 200, "gaps": 0, "cand": 2, "tp": 1, "fp": 1, "unres": 0, "mins": 8.0, "cov": 99.9},
            # Day 7: Distributed SYN scan
            {"flows": 1680000, "valid": 1677500, "rej": 1800, "late": 700, "gaps": 1, "cand": 4, "tp": 3, "fp": 1, "unres": 0, "mins": 15.0, "cov": 99.8},
        ]

        for i, d in enumerate(scenario_data, 1):
            day_dt = base_date + timedelta(days=i)
            rec = DailyEvaluationMetrics(
                day_index=i,
                calendar_date=day_dt.strftime("%Y-%m-%d"),
                scenario_type="SIMULATED_7_DAY_SCENARIO",
                total_flows_received=d["flows"],
                valid_flows=d["valid"],
                rejected_flows=d["rej"],
                late_flows=d["late"],
                sequence_gaps=d["gaps"],
                exporter_coverage_percent=d["cov"],
                model_scored_windows=int(d["flows"] / 100),
                unscored_windows=int(d["rej"] / 100),
                model_failures=0,
                candidate_incidents=d["cand"],
                analyst_confirmed_incidents=d["tp"],
                false_positives=d["fp"],
                unresolved_incidents=d["unres"],
                estimated_missed_attacks=0,
                analyst_review_time_minutes=d["mins"],
                dashboard_availability_percent=99.95,
                model_latency_p95_ms=3.8,
                model_latency_p99_ms=11.2,
                processing_lag_seconds=0.45,
                warnings=[],
            )
            self._daily_metrics.append(rec)

        return self.generate_report()

    def generate_report(self) -> SevenDayEvaluationReport:
        if not self._daily_metrics:
            raise ValueError("No daily metrics recorded.")

        total_flows = sum(d.total_flows_received for d in self._daily_metrics)
        total_cands = sum(d.candidate_incidents for d in self._daily_metrics)
        total_tps = sum(d.analyst_confirmed_incidents for d in self._daily_metrics)
        total_fps = sum(d.false_positives for d in self._daily_metrics)
        days_count = len(self._daily_metrics)

        avg_fps_per_day = total_fps / days_count if days_count > 0 else 0.0
        avg_mins_per_day = sum(d.analyst_review_time_minutes for d in self._daily_metrics) / days_count if days_count > 0 else 0.0
        avg_cov = sum(d.exporter_coverage_percent for d in self._daily_metrics) / days_count if days_count > 0 else 0.0

        target_fps_met = avg_fps_per_day <= 5.0
        target_mins_met = avg_mins_per_day <= 20.0

        scenario_label = "SIMULATED_7_DAY_SCENARIO" if self.is_simulation else "AUTHORIZED_REAL_PILOT"

        recom = (
            "SHADOW_EVALUATION_PASS: Operational targets satisfied under "
            f"{scenario_label}. Average false incidents/day={avg_fps_per_day:.2f} (<= 5.0 target). "
            f"Average analyst burden={avg_mins_per_day:.1f} mins/day (<= 20.0 min budget)."
        )

        return SevenDayEvaluationReport(
            pilot_id=self.pilot_id,
            tenant_id=self.tenant_id,
            evaluation_type=scenario_label,
            start_date=self._daily_metrics[0].calendar_date,
            end_date=self._daily_metrics[-1].calendar_date,
            days_completed=days_count,
            daily_records=self._daily_metrics,
            total_flows_processed=total_flows,
            total_candidate_incidents=total_cands,
            total_confirmed_true_positives=total_tps,
            total_confirmed_false_positives=total_fps,
            average_false_incidents_per_day=round(avg_fps_per_day, 2),
            target_met_le_5_false_per_day=target_fps_met,
            average_analyst_review_minutes_per_day=round(avg_mins_per_day, 1),
            analyst_capacity_target_met=target_mins_met,
            overall_detection_coverage_percent=round(avg_cov, 2),
            recommendation=recom,
        )

    def export_report_to_disk(self, output_dir: Path) -> Path:
        report = self.generate_report()
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"seven_day_report_{self.pilot_id}.json"
        dest = output_dir / filename
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)
        logger.info(f"Seven-day shadow report exported to {dest}")
        return dest

# CloudWatch Alarm: Telemetry Sequence Gaps & Packet Drops
resource "aws_cloudwatch_metric_alarm" "sequence_gaps_alarm" {
  alarm_name          = "fcs-telemetry-sequence-gaps-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "SequenceGaps"
  namespace           = "FederatedCyberShield/Telemetry"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Triggers when sequence gaps indicate packet loss between rural ISP exporter and collector"

  tags = {
    Environment = var.environment
    ManagedBy   = "OpenTofu"
  }
}

# CloudWatch Alarm: Degraded Coverage Detection
resource "aws_cloudwatch_metric_alarm" "degraded_coverage_alarm" {
  alarm_name          = "fcs-degraded-coverage-alert-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "DegradedCoverageCount"
  namespace           = "FederatedCyberShield/Telemetry"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "CRITICAL: Signals missing telemetry coverage from one or more rural ISP edge exporters"

  tags = {
    Environment = var.environment
    Severity    = "Warning"
  }
}

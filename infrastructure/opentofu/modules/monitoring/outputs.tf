output "sequence_gaps_alarm_arn" {
  description = "ARN of the sequence gaps CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.sequence_gaps_alarm.arn
}

output "degraded_coverage_alarm_arn" {
  description = "ARN of the degraded coverage CloudWatch alarm"
  value       = aws_cloudwatch_metric_alarm.degraded_coverage_alarm.arn
}

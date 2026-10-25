output "security_audit_log_group_arn" {
  description = "ARN of the security audit log group"
  value       = aws_cloudwatch_log_group.security_audit_log_group.arn
}

output "collector_log_group_arn" {
  description = "ARN of the collector application log group"
  value       = aws_cloudwatch_log_group.collector_application_logs.arn
}

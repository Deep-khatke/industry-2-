output "collector_role_arn" {
  description = "ARN of the collector IAM role"
  value       = aws_iam_role.collector_role.arn
}

output "auditor_role_arn" {
  description = "ARN of the auditor IAM role"
  value       = aws_iam_role.auditor_role.arn
}

output "tenant_kms_key_arns" {
  description = "Map of tenant_id to dedicated KMS Key ARN"
  value       = { for k, v in aws_kms_key.tenant_key : k => v.arn }
}

output "tenant_key_aliases" {
  description = "Map of tenant_id to KMS Key Alias name"
  value       = { for k, v in aws_kms_alias.tenant_key_alias : k => v.name }
}

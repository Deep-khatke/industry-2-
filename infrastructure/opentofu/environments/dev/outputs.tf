output "vpc_id" {
  description = "ID of the ingestion VPC"
  value       = module.networking.vpc_id
}

output "nlb_dns_name" {
  description = "DNS endpoint of the telemetry ingestion NLB"
  value       = module.ingress.nlb_dns_name
}

output "kinesis_stream_arn" {
  description = "ARN of the telemetry Kinesis data stream"
  value       = module.streaming.stream_arn
}

output "storage_bucket_arn" {
  description = "ARN of the encrypted telemetry archive S3 bucket"
  value       = module.storage.bucket_arn
}

output "tenant_kms_key_arns" {
  description = "Map of tenant IDs to their dedicated KMS key boundaries"
  value       = module.isolation.tenant_kms_key_arns
}

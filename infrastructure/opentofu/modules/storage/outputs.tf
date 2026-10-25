output "bucket_id" {
  description = "ID of the telemetry archive S3 bucket"
  value       = aws_s3_bucket.telemetry_archive.id
}

output "bucket_arn" {
  description = "ARN of the telemetry archive S3 bucket"
  value       = aws_s3_bucket.telemetry_archive.arn
}

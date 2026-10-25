variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "dev"
}

variable "kinesis_stream_arn" {
  description = "ARN of the Kinesis telemetry stream"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the encrypted S3 storage bucket"
  type        = string
}

variable "kms_key_arns" {
  description = "List of KMS Key ARNs allowed for collector encryption"
  type        = list(string)
  default     = []
}

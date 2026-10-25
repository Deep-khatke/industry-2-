variable "bucket_prefix" {
  description = "Prefix for the telemetry archival S3 bucket"
  type        = string
  default     = "fcs-telemetry-archive"
}

variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "dev"
}

variable "kms_key_arn" {
  description = "KMS Key ARN for server-side encryption"
  type        = string
  default     = null
}

variable "retention_days" {
  description = "Days before transitioning objects to Glacier or expiration"
  type        = number
  default     = 90
}

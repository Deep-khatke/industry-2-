variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "dev"
}

variable "retention_days" {
  description = "Log retention period in days"
  type        = number
  default     = 365
}

variable "kms_key_arn" {
  description = "KMS Key ARN for log encryption"
  type        = string
  default     = null
}

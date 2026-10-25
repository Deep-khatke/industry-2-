variable "stream_name" {
  description = "Name of the Kinesis data stream"
  type        = string
  default     = "fcs-telemetry-stream"
}

variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "dev"
}

variable "shard_count" {
  description = "Number of shards for data streaming"
  type        = number
  default     = 2
}

variable "retention_period_hours" {
  description = "Data record retention period in hours"
  type        = number
  default     = 24
}

variable "kms_key_arn" {
  description = "KMS Key ARN for Kinesis server-side encryption"
  type        = string
  default     = null
}

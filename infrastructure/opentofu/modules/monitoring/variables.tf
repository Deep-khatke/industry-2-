variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "dev"
}

variable "kinesis_stream_name" {
  description = "Name of the Kinesis telemetry stream to monitor"
  type        = string
}

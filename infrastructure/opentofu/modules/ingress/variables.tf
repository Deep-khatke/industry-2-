variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "dev"
}

variable "vpc_id" {
  description = "VPC ID where NLB is deployed"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnets for NLB listeners"
  type        = list(string)
}

variable "telemetry_port" {
  description = "UDP port for NetFlow/IPFIX telemetry"
  type        = number
  default     = 2055
}

variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "Target AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "tenant_ids" {
  description = "List of simulated rural ISP tenant identifiers"
  type        = list(string)
  default = [
    "tenant-isp-alpha",
    "tenant-isp-beta",
    "tenant-isp-gamma",
    "tenant-isp-delta",
    "tenant-isp-epsilon",
    "tenant-isp-zeta",
    "tenant-isp-eta",
  ]
}

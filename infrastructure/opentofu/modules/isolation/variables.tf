variable "tenant_ids" {
  description = "List of simulated tenant IDs to establish cryptographic KMS boundaries for"
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

variable "environment" {
  description = "Environment identifier"
  type        = string
  default     = "dev"
}

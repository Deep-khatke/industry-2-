variable "vpc_cidr" {
  description = "CIDR block for the FCS ingestion VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "environment" {
  description = "Deployment environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "availability_zones" {
  description = "List of availability zones for multi-AZ resilience"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private collector subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public NLB ingress subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "allowed_isp_cidrs" {
  description = "Authorized rural ISP egress IP ranges allowed to stream UDP telemetry"
  type        = list(string)
  default     = ["10.100.0.0/16"]
}

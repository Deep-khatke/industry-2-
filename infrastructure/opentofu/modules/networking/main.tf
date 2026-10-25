resource "aws_vpc" "fcs_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "fcs-telemetry-vpc-${var.environment}"
    Environment = var.environment
    ManagedBy   = "OpenTofu"
    Project     = "FederatedCyberShield"
  }
}

resource "aws_subnet" "public" {
  count             = length(var.public_subnet_cidrs)
  vpc_id            = aws_vpc.fcs_vpc.id
  cidr_block        = var.public_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  # Critical security setting: Do not assign public IPs automatically to instances
  map_public_ip_on_launch = false

  tags = {
    Name        = "fcs-public-subnet-${count.index}-${var.environment}"
    Environment = var.environment
    Tier        = "Ingress"
  }
}

resource "aws_subnet" "private" {
  count             = length(var.private_subnet_cidrs)
  vpc_id            = aws_vpc.fcs_vpc.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  map_public_ip_on_launch = false

  tags = {
    Name        = "fcs-private-collector-subnet-${count.index}-${var.environment}"
    Environment = var.environment
    Tier        = "Processing"
  }
}

# Ingress Security Group: Bounded UDP port 2055 strictly to registered ISP subnets
resource "aws_security_group" "telemetry_ingress" {
  name        = "fcs-telemetry-ingress-sg-${var.environment}"
  description = "Allows UDP NetFlow/IPFIX from registered ISP CIDRs only; strictly no SSH or administrative ingress"
  vpc_id      = aws_vpc.fcs_vpc.id

  ingress {
    description = "IPFIX UDP telemetry from authorized rural ISP gateways"
    from_port   = 2055
    to_port     = 2055
    protocol    = "udp"
    cidr_blocks = var.allowed_isp_cidrs
  }

  egress {
    description = "Outbound egress restricted to VPC private endpoints"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = {
    Name        = "fcs-telemetry-ingress-sg-${var.environment}"
    Environment = var.environment
    Policy      = "LeastPrivilege"
  }
}

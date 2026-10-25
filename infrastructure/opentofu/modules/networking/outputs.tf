output "vpc_id" {
  description = "ID of the FCS Ingestion VPC"
  value       = aws_vpc.fcs_vpc.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.fcs_vpc.cidr_block
}

output "private_subnet_ids" {
  description = "IDs of the private collector subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "IDs of the public NLB subnets"
  value       = aws_subnet.public[*].id
}

output "telemetry_ingress_sg_id" {
  description = "ID of the telemetry ingress security group"
  value       = aws_security_group.telemetry_ingress.id
}

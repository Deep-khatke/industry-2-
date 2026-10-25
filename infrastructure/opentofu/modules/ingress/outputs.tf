output "nlb_dns_name" {
  description = "DNS name of the Network Load Balancer"
  value       = aws_lb.telemetry_nlb.dns_name
}

output "nlb_arn" {
  description = "ARN of the Network Load Balancer"
  value       = aws_lb.telemetry_nlb.arn
}

output "target_group_arn" {
  description = "ARN of the collector target group"
  value       = aws_lb_target_group.telemetry_tg.arn
}

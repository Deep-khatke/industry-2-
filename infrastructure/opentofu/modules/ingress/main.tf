# Network Load Balancer (NLB) for high-throughput UDP telemetry ingest
resource "aws_lb" "telemetry_nlb" {
  name               = "fcs-telemetry-nlb-${var.environment}"
  internal           = false
  load_balancer_type = "network"
  subnets            = var.public_subnet_ids

  enable_deletion_protection = false

  tags = {
    Name        = "fcs-telemetry-nlb-${var.environment}"
    Environment = var.environment
    ManagedBy   = "OpenTofu"
  }
}

resource "aws_lb_target_group" "telemetry_tg" {
  name        = "fcs-telemetry-tg-${var.environment}"
  port        = var.telemetry_port
  protocol    = "UDP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    protocol            = "TCP"
    port                = 8080 # Lightweight health check endpoint on collector
    interval            = 30
    healthy_threshold   = 3
    unhealthy_threshold = 3
  }

  tags = {
    Name        = "fcs-telemetry-tg-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_lb_listener" "udp_listener" {
  load_balancer_arn = aws_lb.telemetry_nlb.arn
  port              = var.telemetry_port
  protocol          = "UDP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.telemetry_tg.arn
  }
}

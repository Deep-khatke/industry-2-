# Telemetry Collector Service Role (Least Privilege)
resource "aws_iam_role" "collector_role" {
  name        = "fcs-telemetry-collector-role-${var.environment}"
  description = "Execution role for FCS Telemetry Collector instance with bounded permissions"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Service     = "TelemetryCollector"
    ManagedBy   = "OpenTofu"
  }
}

# Policy allowing strictly PutRecord / PutRecords to the designated Kinesis stream
resource "aws_iam_policy" "collector_kinesis_policy" {
  name        = "fcs-collector-kinesis-put-${var.environment}"
  description = "Allows publishing normalized telemetry events to designated Kinesis stream only"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kinesis:PutRecord",
          "kinesis:PutRecords",
          "kinesis:DescribeStream"
        ]
        Resource = var.kinesis_stream_arn
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "FederatedCyberShield/Telemetry"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "collector_kinesis_attach" {
  role       = aws_iam_role.collector_role.name
  policy_arn = aws_iam_policy.collector_kinesis_policy.arn
}

# Auditor Read-Only Role
resource "aws_iam_role" "auditor_role" {
  name        = "fcs-platform-auditor-role-${var.environment}"
  description = "Read-only role for security and compliance audits; strictly no access to telemetry payloads"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::123456789012:root" # Place-holder account
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Role        = "PlatformAuditor"
  }
}

resource "aws_iam_policy" "auditor_policy" {
  name        = "fcs-auditor-policy-${var.environment}"
  description = "Allows inspection of metrics, alarms, and audit logs without payload access"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:GetMetricData",
          "cloudwatch:ListMetrics",
          "cloudwatch:DescribeAlarms",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:GetLogEvents",
          "logs:FilterLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "auditor_attach" {
  role       = aws_iam_role.auditor_role.name
  policy_arn = aws_iam_policy.auditor_policy.arn
}

output "stream_name" {
  description = "Name of the Kinesis telemetry stream"
  value       = aws_kinesis_stream.telemetry_stream.name
}

output "stream_arn" {
  description = "ARN of the Kinesis telemetry stream"
  value       = aws_kinesis_stream.telemetry_stream.arn
}

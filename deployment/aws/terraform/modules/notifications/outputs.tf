# =============================================================================
# NOTIFICATIONS MODULE - OUTPUTS
# =============================================================================

output "sns_topic_arn" {
  description = "SNS topic ARN for notifications"
  value       = aws_sns_topic.scraper_notifications.arn
}

output "sns_topic_name" {
  description = "SNS topic name"
  value       = aws_sns_topic.scraper_notifications.name
}

output "lambda_function_arn" {
  description = "Lambda function ARN for Slack/Teams notifications"
  value       = aws_lambda_function.notifications.arn
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.notifications.function_name
}

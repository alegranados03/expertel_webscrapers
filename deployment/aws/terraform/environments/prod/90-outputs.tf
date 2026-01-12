# =============================================================================
# OUTPUTS
# =============================================================================

# -----------------------------------------------------------------------------
# INSTANCE
# -----------------------------------------------------------------------------

output "instance_id" {
  description = "Scraper EC2 instance ID"
  value       = module.scraper_instance.instance_id
}

output "instance_public_ip" {
  description = "Scraper instance public IP"
  value       = module.scraper_instance.instance_public_ip
}

output "instance_private_ip" {
  description = "Scraper instance private IP"
  value       = module.scraper_instance.instance_private_ip
}

# -----------------------------------------------------------------------------
# ACCESS
# -----------------------------------------------------------------------------

output "novnc_url" {
  description = "noVNC access URL"
  value       = module.scraper_instance.novnc_url
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = module.scraper_instance.ssh_command
}

# -----------------------------------------------------------------------------
# NOTIFICATIONS
# -----------------------------------------------------------------------------

output "sns_topic_arn" {
  description = "SNS topic ARN for notifications"
  value       = module.notifications.sns_topic_arn
}

# -----------------------------------------------------------------------------
# CI/CD
# -----------------------------------------------------------------------------

output "codebuild_project_name" {
  description = "CodeBuild project name"
  value       = module.codebuild.project_name
}

output "codebuild_webhook_url" {
  description = "GitHub webhook URL (configure in GitHub)"
  value       = module.codebuild.webhook_url
}

# -----------------------------------------------------------------------------
# LOGS
# -----------------------------------------------------------------------------

output "cloudwatch_log_group" {
  description = "CloudWatch log group for scraper logs"
  value       = module.scraper_instance.cloudwatch_log_group
}

# -----------------------------------------------------------------------------
# NETWORK
# -----------------------------------------------------------------------------

output "vpc_id" {
  description = "VPC ID (from backend)"
  value       = data.aws_vpc.backend.id
}

output "security_group_id" {
  description = "Scraper security group ID"
  value       = module.scraper_instance.security_group_id
}

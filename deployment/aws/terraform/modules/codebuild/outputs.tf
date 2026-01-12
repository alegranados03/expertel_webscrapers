# =============================================================================
# CODEBUILD MODULE - OUTPUTS
# =============================================================================

output "project_name" {
  description = "CodeBuild project name"
  value       = aws_codebuild_project.scraper.name
}

output "project_arn" {
  description = "CodeBuild project ARN"
  value       = aws_codebuild_project.scraper.arn
}

output "role_arn" {
  description = "CodeBuild IAM role ARN"
  value       = aws_iam_role.codebuild.arn
}

output "webhook_url" {
  description = "GitHub webhook URL"
  value       = var.enable_webhook ? aws_codebuild_webhook.github[0].payload_url : null
}

output "cache_bucket" {
  description = "S3 bucket for CodeBuild cache"
  value       = aws_s3_bucket.codebuild_cache.bucket
}

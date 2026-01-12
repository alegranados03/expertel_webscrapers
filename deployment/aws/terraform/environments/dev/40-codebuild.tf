# =============================================================================
# CODEBUILD CI/CD
# =============================================================================

module "codebuild" {
  source = "../../modules/codebuild"

  app_name    = var.app_name
  environment = var.environment
  aws_region  = var.aws_region

  # GitHub
  github_repository_url = var.github_repository_url
  source_branch         = var.github_branch
  buildspec_file        = "buildspec.yml"

  # Deployment target
  instance_id   = module.scraper_instance.instance_id
  sns_topic_arn = module.notifications.sns_topic_arn

  # CI/CD automation
  enable_webhook = var.enable_webhook

  log_retention_days = var.log_retention_days

  tags = local.common_tags

  depends_on = [module.scraper_instance]
}

# =============================================================================
# NOTIFICATIONS
# =============================================================================

module "notifications" {
  source = "../../modules/notifications"

  app_name            = var.app_name
  environment         = var.environment
  aws_region          = var.aws_region
  aws_account_id      = data.aws_caller_identity.current.account_id
  notification_emails = var.notification_emails
  log_retention_days  = var.log_retention_days

  tags = local.common_tags
}

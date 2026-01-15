# =============================================================================
# SSM PARAMETERS (Non-secret configuration)
# =============================================================================
# These parameters are auto-generated from Terraform outputs
# Secrets are managed separately via manage-secrets.sh
# =============================================================================

# -----------------------------------------------------------------------------
# DATABASE CONFIGURATION (from backend app-settings JSON)
# -----------------------------------------------------------------------------

resource "aws_ssm_parameter" "db_host" {
  name        = "/${var.app_name}/${var.environment}/database/host"
  description = "PostgreSQL host (from backend app-settings)"
  type        = "String"
  value       = local.db_host

  tags = local.common_tags
}

resource "aws_ssm_parameter" "db_name" {
  name        = "/${var.app_name}/${var.environment}/database/name"
  description = "PostgreSQL database name (from backend app-settings)"
  type        = "String"
  value       = local.db_name

  tags = local.common_tags
}

resource "aws_ssm_parameter" "db_port" {
  name        = "/${var.app_name}/${var.environment}/database/port"
  description = "PostgreSQL port (from backend app-settings)"
  type        = "String"
  value       = local.db_port

  tags = local.common_tags
}

resource "aws_ssm_parameter" "db_username" {
  name        = "/${var.app_name}/${var.environment}/database/username"
  description = "PostgreSQL username (from backend app-settings)"
  type        = "String"
  value       = local.db_user

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# BACKEND API CONFIGURATION
# -----------------------------------------------------------------------------

resource "aws_ssm_parameter" "backend_url" {
  name        = "/${var.app_name}/${var.environment}/backend-api/url"
  description = "Backend API URL (from backend alb-url, already includes http://)"
  type        = "String"
  value       = data.aws_ssm_parameter.backend_url.value

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# AZURE CONFIGURATION (non-secret parts)
# -----------------------------------------------------------------------------

resource "aws_ssm_parameter" "azure_user_email" {
  name        = "/${var.app_name}/${var.environment}/azure/user-email"
  description = "Azure user email for notifications"
  type        = "String"
  value       = "notifications@expertel.com"

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# MFA SERVICE
# -----------------------------------------------------------------------------

resource "aws_ssm_parameter" "mfa_service_url" {
  name        = "/${var.app_name}/${var.environment}/mfa-service/url"
  description = "MFA service URL"
  type        = "String"
  value       = "http://localhost:7000"  # Update with actual MFA service URL

  tags = local.common_tags
}

# -----------------------------------------------------------------------------
# INSTANCE INFO
# -----------------------------------------------------------------------------

resource "aws_ssm_parameter" "instance_id" {
  name        = "/${var.app_name}/${var.environment}/instance/id"
  description = "Scraper EC2 instance ID"
  type        = "String"
  value       = module.scraper_instance.instance_id

  tags = local.common_tags
}

resource "aws_ssm_parameter" "novnc_url" {
  name        = "/${var.app_name}/${var.environment}/config/novnc-url"
  description = "noVNC access URL"
  type        = "String"
  value       = "https://${module.scraper_instance.instance_public_ip}/vnc/"

  tags = local.common_tags
}

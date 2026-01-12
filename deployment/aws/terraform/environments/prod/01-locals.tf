# =============================================================================
# LOCAL VARIABLES
# =============================================================================

locals {
  name_prefix = "${var.app_name}-${var.environment}"

  common_tags = {
    Project     = "ExpertelIQ2"
    Component   = "Scraper"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  # Backend app name for referencing backend resources
  backend_app_name = "experteliq2-backend"
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}

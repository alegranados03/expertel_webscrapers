# =============================================================================
# NOTIFICATIONS MODULE - VARIABLES
# =============================================================================

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "experteliq2-scraper"
}

variable "environment" {
  description = "Environment (dev, qa, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "notification_emails" {
  description = "List of email addresses to receive notifications"
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

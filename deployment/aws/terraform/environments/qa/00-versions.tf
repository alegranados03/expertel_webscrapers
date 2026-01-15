# =============================================================================
# TERRAFORM VERSIONS AND PROVIDERS
# =============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }

  backend "s3" {
    bucket       = "experteliq2-scraper-terraform-state-qa"
    key          = "scraper/qa/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ExpertelIQ2"
      Component   = "Scraper"
      Environment = "qa"
      ManagedBy   = "Terraform"
    }
  }
}

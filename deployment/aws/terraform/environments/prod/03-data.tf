# =============================================================================
# DATA SOURCES
# =============================================================================
# Reference existing resources from the backend infrastructure

# -----------------------------------------------------------------------------
# VPC AND NETWORKING (from backend)
# -----------------------------------------------------------------------------

# Get the VPC created by the backend
data "aws_vpc" "backend" {
  tags = {
    Name        = "${local.backend_app_name}-${var.environment}-vpc"
    Environment = var.environment
  }
}

# Get public subnets from the backend VPC
data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.backend.id]
  }

  tags = {
    Type = "public"
  }
}

# -----------------------------------------------------------------------------
# SECURITY GROUPS (from backend)
# -----------------------------------------------------------------------------

# Get the database security group to allow scraper access
data "aws_security_group" "database" {
  tags = {
    Name        = "${local.backend_app_name}-${var.environment}-database-sg"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# SSM PARAMETERS (from backend)
# -----------------------------------------------------------------------------

# Get database host from backend SSM
data "aws_ssm_parameter" "db_host" {
  name = "/${local.backend_app_name}/${var.environment}/database/host"
}

# Get backend ALB URL
data "aws_ssm_parameter" "backend_url" {
  name = "/${local.backend_app_name}/${var.environment}/config/alb-url"
}

# -----------------------------------------------------------------------------
# AMI
# -----------------------------------------------------------------------------

# Get latest Ubuntu 22.04 AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# -----------------------------------------------------------------------------
# S3 BUCKET (from backend, for file storage)
# -----------------------------------------------------------------------------

data "aws_s3_bucket" "backend" {
  bucket = "${local.backend_app_name}-${var.environment}-storage"
}

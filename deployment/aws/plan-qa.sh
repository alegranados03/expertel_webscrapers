#!/bin/bash
# =============================================================================
# ExpertelIQ2 Scraper - Plan QA Environment
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/terraform/environments/qa"

echo "=========================================="
echo "ExpertelIQ2 Scraper - Plan QA"
echo "=========================================="

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo "Error: Terraform is not installed"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured"
    exit 1
fi

cd "$TERRAFORM_DIR"

echo "Initializing Terraform..."
terraform init

echo ""
echo "Planning changes..."
terraform plan

echo ""
echo "=========================================="
echo "Plan complete. Review changes above."
echo "To apply: ./deploy-qa.sh"
echo "=========================================="

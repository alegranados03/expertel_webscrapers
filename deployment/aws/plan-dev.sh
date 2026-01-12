#!/bin/bash
# ExpertelIQ2 Scraper - Plan DEV Environment
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/terraform/environments/dev"

echo "=========================================="
echo "ExpertelIQ2 Scraper - Plan DEV"
echo "=========================================="

if ! command -v terraform &> /dev/null; then
    echo "Error: Terraform is not installed"
    exit 1
fi

cd "$TERRAFORM_DIR"
terraform init
terraform plan

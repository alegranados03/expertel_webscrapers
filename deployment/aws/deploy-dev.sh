#!/bin/bash
# ExpertelIQ2 Scraper - Deploy DEV Environment
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/terraform/environments/dev"

echo "=========================================="
echo "ExpertelIQ2 Scraper - Deploy DEV"
echo "=========================================="

"$SCRIPT_DIR/manage-secrets.sh" validate dev || {
    echo "Run: ./manage-secrets.sh setup dev"
    exit 1
}

cd "$TERRAFORM_DIR"
terraform init
terraform plan -out=tfplan

read -p "Apply changes? (yes/no): " confirm
[ "$confirm" != "yes" ] && { rm -f tfplan; exit 0; }

terraform apply tfplan
rm -f tfplan

echo "Deployment Complete!"
terraform output novnc_url

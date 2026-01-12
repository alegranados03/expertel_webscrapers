#!/bin/bash
# ExpertelIQ2 Scraper - Deploy PROD Environment
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/terraform/environments/prod"

echo "=========================================="
echo "ExpertelIQ2 Scraper - Deploy PROD"
echo "=========================================="
echo "WARNING: This is PRODUCTION environment!"
echo "=========================================="

"$SCRIPT_DIR/manage-secrets.sh" validate prod || {
    echo "Run: ./manage-secrets.sh setup prod"
    exit 1
}

cd "$TERRAFORM_DIR"
terraform init
terraform plan -out=tfplan

echo ""
echo "PRODUCTION DEPLOYMENT - Please review carefully!"
read -p "Type 'yes' to confirm PRODUCTION deployment: " confirm
[ "$confirm" != "yes" ] && { rm -f tfplan; exit 0; }

terraform apply tfplan
rm -f tfplan

echo "PRODUCTION Deployment Complete!"
terraform output novnc_url

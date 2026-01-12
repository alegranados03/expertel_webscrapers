# AWS Deployment Scripts

## Quick Reference

| Command | Description |
|---------|-------------|
| `./manage-secrets.sh setup <env>` | Configure secrets interactively |
| `./manage-secrets.sh validate <env>` | Validate all secrets exist |
| `./plan-<env>.sh` | Preview Terraform changes |
| `./deploy-<env>.sh` | Deploy infrastructure |

## Environments

- `dev` - Development
- `qa` - Quality Assurance
- `prod` - Production

## First-Time Setup

```bash
# 1. Create S3 bucket for Terraform state
aws s3 mb s3://experteliq2-scraper-terraform-state-qa --region us-east-2

# 2. Configure secrets
./manage-secrets.sh setup qa

# 3. Deploy
./deploy-qa.sh
```

## Secrets Required

| Secret | Description |
|--------|-------------|
| `database/password` | PostgreSQL password |
| `backend-api/key` | Backend API key |
| `cryptography/key` | Encryption key |
| `azure/client-id` | Azure AD client ID |
| `azure/tenant-id` | Azure AD tenant ID |
| `azure/client-secret` | Azure AD secret |
| `novnc/password` | noVNC access password |
| `slack/webhook-url` | Slack notifications (optional) |
| `teams/webhook-url` | Teams notifications (optional) |

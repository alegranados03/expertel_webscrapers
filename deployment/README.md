# ExpertelIQ2 Webscrapers - Deployment Guide

## Overview

This deployment creates an AWS EC2 instance with:
- **Ubuntu 22.04** with XFCE desktop environment
- **noVNC** for remote desktop access via browser
- **Python 3.11 + Playwright** for web scraping
- **Scheduled execution** at 23:00 and 12:00 EST daily
- **Multi-channel notifications** (Email, Slack, Teams)
- **CI/CD pipeline** with AWS CodeBuild

## Architecture

```
Internet → Nginx (HTTPS + Auth) → noVNC → XFCE Desktop
                                            │
                      ┌─────────────────────┤
                      ▼                     ▼
              Chrome/Playwright    Systemd Timer (23:00 & 12:00 EST)
                      │                     │
                      └─────────────────────┘
                              │
                              ▼
                    PostgreSQL + MongoDB (VPC interno)
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.0 installed
3. **Backend infrastructure** already deployed (VPC, databases)
4. **SSH key pair** created in AWS

## Quick Start

### 1. Create S3 Bucket for Terraform State

```bash
# For QA environment
aws s3 mb s3://experteliq2-scraper-terraform-state-qa --region us-east-2
```

### 2. Configure Secrets

```bash
# Linux/Mac
./deployment/aws/manage-secrets.sh setup qa

# Windows
.\deployment\windows\Manage-Secrets.ps1 -Command setup -Environment qa
```

Required secrets:
- PostgreSQL password
- Backend API key
- Cryptography key
- Azure AD credentials (client ID, tenant ID, client secret)
- noVNC access password
- Slack webhook URL (optional)
- Teams webhook URL (optional)

### 3. Deploy Infrastructure

```bash
# Linux/Mac
./deployment/aws/deploy-qa.sh

# Windows
.\deployment\windows\Deploy-Environment.ps1 -Environment qa
```

### 4. Access noVNC

After deployment (~5-10 minutes for initialization):

1. Get the noVNC URL from Terraform output
2. Open in browser: `https://<instance-ip>/vnc/`
3. Enter username: `scraper`
4. Enter password: (the noVNC password you configured)

## File Structure

```
deployment/
├── PLAN.md                     # Detailed implementation plan
├── README.md                   # This file
│
├── aws/
│   ├── manage-secrets.sh       # Secrets management (Linux/Mac)
│   ├── plan-qa.sh              # Plan changes
│   ├── deploy-qa.sh            # Deploy infrastructure
│   │
│   └── terraform/
│       ├── environments/
│       │   ├── qa/             # QA environment config
│       │   ├── dev/            # Dev environment config
│       │   └── prod/           # Prod environment config
│       │
│       └── modules/
│           ├── scraper-instance/   # EC2 + noVNC
│           ├── notifications/      # SNS + Lambda
│           └── codebuild/          # CI/CD
│
└── windows/
    ├── Manage-Secrets.ps1      # Secrets management (Windows)
    └── Deploy-Environment.ps1  # Deploy infrastructure
```

## Scheduled Execution

The scraper runs automatically at:
- **23:00 EST** (04:00 UTC)
- **12:00 EST** (17:00 UTC)

Check timer status:
```bash
ssh ubuntu@<instance-ip> "systemctl status scraper.timer"
```

View execution logs:
```bash
ssh ubuntu@<instance-ip> "journalctl -u scraper.service -f"
```

## Manual Execution

To run the scraper manually:

1. Connect via noVNC
2. Open terminal in XFCE
3. Run:
```bash
cd /opt/experteliq2-scraper
poetry run python main.py
```

## CI/CD Pipeline

### Automatic Deployment

1. Enable webhook in Terraform: set `enable_webhook = true`
2. Apply changes: `./deploy-qa.sh`
3. Configure webhook in GitHub:
   - Go to repo Settings → Webhooks
   - Add webhook URL from Terraform output
   - Set content type: `application/json`

### Manual Deployment

```bash
aws codebuild start-build \
  --project-name experteliq2-scraper-qa \
  --source-version main \
  --region us-east-2
```

## Notifications

### Channels

| Channel | Configuration |
|---------|--------------|
| Email | Add emails to `notification_emails` variable |
| Slack | Configure `slack/webhook-url` in SSM |
| Teams | Configure `teams/webhook-url` in SSM |

### Events Notified

- Deployment started/completed/failed
- Scheduled execution started/completed
- Scraper errors

## Troubleshooting

### Cannot Access noVNC

1. Check security group allows HTTPS (443) from your IP
2. Verify Nginx is running: `systemctl status nginx`
3. Check VNC is running: `systemctl status vncserver`

### Scraper Not Running

1. Check timer is active: `systemctl status scraper.timer`
2. View logs: `journalctl -u scraper.service -n 100`
3. Check .env file exists: `cat /opt/experteliq2-scraper/.env`

### Database Connection Issues

1. Verify security group allows connection to database
2. Check SSM parameters are correct
3. Test connection: `psql -h <host> -U experteliq2 -d experteliq2_qa`

## Costs

| Resource | Monthly Cost |
|----------|-------------|
| EC2 t3.medium | ~$30 |
| EBS 50GB gp3 | ~$8 |
| Data transfer | ~$5 |
| CloudWatch Logs | ~$5 |
| Other (SNS, Lambda) | ~$5 |
| **Total** | **~$53/month** |

## Security Considerations

1. noVNC is protected by:
   - HTTPS encryption
   - Basic authentication
   - Self-signed certificate (replace with Let's Encrypt for production)

2. Database access:
   - Only from within VPC
   - Security group restricted to scraper instance

3. Secrets:
   - Stored in SSM Parameter Store with encryption
   - Decrypted only at runtime

## Support

For issues or questions:
- Check CloudWatch logs: `/experteliq2/scraper/<env>`
- Review instance logs: `/var/log/user-data.log`
- Contact the development team

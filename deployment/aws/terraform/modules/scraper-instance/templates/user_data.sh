#!/bin/bash
# =============================================================================
# ExpertelIQ2 Webscrapers - EC2 User Data Script
# =============================================================================
# Sets up Ubuntu 22.04 with:
# - XFCE desktop environment
# - noVNC for remote browser access
# - Python 3.11 + Poetry + Playwright
# - Systemd timers for scheduled execution (23:00 & 12:00 EST)
# =============================================================================

set -e

# Logging setup
exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1
echo "=============================================="
echo "Starting ExpertelIQ2 Scraper deployment"
echo "Date: $(date)"
echo "=============================================="

# Configuration from Terraform
ENVIRONMENT="${environment}"
APP_NAME="${app_name}"
AWS_REGION="${aws_region}"
GITHUB_REPO_URL="${github_repo_url}"
GITHUB_BRANCH="${github_branch}"
SNS_TOPIC_ARN="${sns_topic_arn}"
SCREEN_RESOLUTION="${screen_resolution}"
TIMEZONE="${timezone}"

echo "Environment: $ENVIRONMENT"
echo "App Name: $APP_NAME"
echo "AWS Region: $AWS_REGION"
echo "GitHub Repo: $GITHUB_REPO_URL"
echo "Branch: $GITHUB_BRANCH"
echo "Timezone: $TIMEZONE"
echo "Screen Resolution: $SCREEN_RESOLUTION"

# =============================================================================
# SYSTEM UPDATE & BASE PACKAGES
# =============================================================================

echo "Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y

echo "Installing base packages..."
apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    jq \
    htop \
    vim \
    net-tools \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# =============================================================================
# SET TIMEZONE
# =============================================================================

echo "Setting timezone to $TIMEZONE..."
timedatectl set-timezone $TIMEZONE

# =============================================================================
# INSTALL AWS CLI v2
# =============================================================================

echo "Installing AWS CLI v2..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
./aws/install
rm -rf aws awscliv2.zip

export AWS_DEFAULT_REGION=$AWS_REGION

# =============================================================================
# INSTALL XFCE DESKTOP + VNC
# =============================================================================

echo "Installing XFCE desktop environment..."
apt-get install -y \
    xfce4 \
    xfce4-goodies \
    xfonts-base \
    xfonts-100dpi \
    xfonts-75dpi \
    dbus-x11

echo "Installing VNC and noVNC..."
apt-get install -y \
    tigervnc-standalone-server \
    tigervnc-common \
    novnc \
    websockify

# =============================================================================
# INSTALL NGINX FOR SSL TERMINATION
# =============================================================================

echo "Installing Nginx..."
apt-get install -y nginx apache2-utils

# =============================================================================
# INSTALL PYTHON 3.11 + POETRY
# =============================================================================

echo "Installing Python 3.11..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -y
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip

# Set Python 3.11 as default
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

echo "Installing Poetry..."
curl -sSL https://install.python-poetry.org | python3 -
echo 'export PATH="$HOME/.local/bin:$PATH"' >> /root/.bashrc
export PATH="/root/.local/bin:$PATH"

# =============================================================================
# INSTALL GOOGLE CHROME
# =============================================================================

echo "Installing Google Chrome..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
apt-get update -y
apt-get install -y google-chrome-stable

# =============================================================================
# CREATE APPLICATION USER
# =============================================================================

echo "Creating application user..."
useradd -m -s /bin/bash scraper
usermod -aG sudo scraper

# Setup .bashrc for scraper user
cat >> /home/scraper/.bashrc << 'EOF'
export PATH="$HOME/.local/bin:$PATH"
export DISPLAY=:99
EOF

# =============================================================================
# CLONE APPLICATION
# =============================================================================

echo "Cloning application repository..."
APP_DIR="/opt/$APP_NAME"
mkdir -p $APP_DIR
cd $APP_DIR

git clone --branch $GITHUB_BRANCH $GITHUB_REPO_URL .
chown -R scraper:scraper $APP_DIR

# =============================================================================
# INSTALL PYTHON DEPENDENCIES
# =============================================================================

echo "Installing Python dependencies..."
cd $APP_DIR
sudo -u scraper /root/.local/bin/poetry config virtualenvs.in-project true
sudo -u scraper /root/.local/bin/poetry install --no-interaction

# Install Playwright browsers
echo "Installing Playwright browsers..."
sudo -u scraper /root/.local/bin/poetry run playwright install chromium
sudo -u scraper /root/.local/bin/poetry run playwright install-deps

# =============================================================================
# FETCH SECRETS FROM SSM
# =============================================================================

echo "Fetching configuration from SSM..."

get_ssm_parameter() {
    local param_name=$1
    aws ssm get-parameter \
        --name "$param_name" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text 2>/dev/null || echo ""
}

# Fetch all required parameters
DB_HOST=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/database/host")
DB_NAME=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/database/name")
DB_PORT=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/database/port")
DB_USERNAME=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/database/username")
DB_PASSWORD=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/database/password")
BACKEND_API_URL=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/backend-api/url")
BACKEND_API_KEY=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/backend-api/key")
CRYPTOGRAPHY_KEY=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/cryptography/key")
AZURE_CLIENT_ID=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/azure/client-id")
AZURE_TENANT_ID=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/azure/tenant-id")
AZURE_CLIENT_SECRET=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/azure/client-secret")
AZURE_USER_EMAIL=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/azure/user-email")
ANTHROPIC_API_KEY=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/anthropic/api-key")
MFA_SERVICE_URL=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/mfa-service/url")
NOVNC_PASSWORD=$(get_ssm_parameter "/$APP_NAME/$ENVIRONMENT/novnc/password")

# Create .env file
echo "Creating environment configuration..."
cat > $APP_DIR/.env << EOF
# ExpertelIQ2 Scraper - Generated $(date)
# Environment: $ENVIRONMENT

# Database
DB_HOST=$DB_HOST
DB_NAME=$DB_NAME
DB_PORT=$DB_PORT
DB_USERNAME=$DB_USERNAME
DB_PASSWORD=$DB_PASSWORD

# Backend API
EIQ_BACKEND_API_BASE_URL=$BACKEND_API_URL
EIQ_BACKEND_API_KEY=$BACKEND_API_KEY

# Cryptography
CRYPTOGRAPHY_KEY=$CRYPTOGRAPHY_KEY

# Azure (for email notifications)
CLIENT_ID=$AZURE_CLIENT_ID
TENANT_ID=$AZURE_TENANT_ID
CLIENT_SECRET=$AZURE_CLIENT_SECRET
USER_EMAIL=$AZURE_USER_EMAIL

# Anthropic
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY

# MFA Service
MFA_SERVICE_URL=$MFA_SERVICE_URL

# Environment
ENVIRONMENT=$ENVIRONMENT
SNS_TOPIC_ARN=$SNS_TOPIC_ARN
EOF

chown scraper:scraper $APP_DIR/.env
chmod 600 $APP_DIR/.env

# =============================================================================
# CONFIGURE VNC
# =============================================================================

echo "Configuring VNC..."
mkdir -p /home/scraper/.vnc

# Set VNC password
echo "$NOVNC_PASSWORD" | vncpasswd -f > /home/scraper/.vnc/passwd
chmod 600 /home/scraper/.vnc/passwd

# VNC startup script
cat > /home/scraper/.vnc/xstartup << 'EOF'
#!/bin/bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export XKL_XMODMAP_DISABLE=1
exec startxfce4
EOF
chmod +x /home/scraper/.vnc/xstartup

chown -R scraper:scraper /home/scraper/.vnc

# =============================================================================
# CONFIGURE NGINX FOR NOVNC
# =============================================================================

echo "Configuring Nginx..."

# Create htpasswd for basic auth
htpasswd -cb /etc/nginx/.htpasswd scraper "$NOVNC_PASSWORD"

# Nginx configuration
cat > /etc/nginx/sites-available/novnc << 'EOF'
server {
    listen 80;
    server_name _;

    # Redirect to HTTPS
    location / {
        return 301 https://$host$request_uri;
    }

    # ACME challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
}

server {
    listen 443 ssl;
    server_name _;

    # Self-signed cert initially (replace with Let's Encrypt later)
    ssl_certificate /etc/nginx/ssl/nginx.crt;
    ssl_certificate_key /etc/nginx/ssl/nginx.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Basic authentication
    auth_basic "Scraper Access";
    auth_basic_user_file /etc/nginx/.htpasswd;

    # noVNC static files
    location /vnc/ {
        alias /usr/share/novnc/;
        index vnc.html;
        try_files $uri $uri/ /vnc/vnc.html;
    }

    # WebSocket proxy to VNC
    location /websockify {
        proxy_pass http://127.0.0.1:6080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
EOF

# Create self-signed certificate (temporary)
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/nginx.key \
    -out /etc/nginx/ssl/nginx.crt \
    -subj "/C=US/ST=State/L=City/O=Expertel/CN=scraper-$ENVIRONMENT.expertel.com"

# Enable site
ln -sf /etc/nginx/sites-available/novnc /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl restart nginx

# =============================================================================
# CREATE SYSTEMD SERVICES
# =============================================================================

echo "Creating systemd services..."

# VNC Service
cat > /etc/systemd/system/vncserver.service << EOF
[Unit]
Description=TigerVNC Server
After=network.target

[Service]
Type=simple
User=scraper
Group=scraper
WorkingDirectory=/home/scraper
Environment=DISPLAY=:99
ExecStartPre=/bin/sh -c 'rm -f /tmp/.X99-lock /tmp/.X11-unix/X99'
ExecStart=/usr/bin/vncserver :99 -geometry $SCREEN_RESOLUTION -depth 24 -fg
ExecStop=/usr/bin/vncserver -kill :99
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Websockify Service (noVNC bridge)
cat > /etc/systemd/system/websockify.service << EOF
[Unit]
Description=Websockify for noVNC
After=vncserver.service
Requires=vncserver.service

[Service]
Type=simple
User=scraper
ExecStart=/usr/bin/websockify --web=/usr/share/novnc 6080 localhost:5999
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Scraper Service
cat > /etc/systemd/system/scraper.service << EOF
[Unit]
Description=ExpertelIQ2 Webscraper
After=network.target vncserver.service
Wants=vncserver.service

[Service]
Type=oneshot
User=scraper
Group=scraper
WorkingDirectory=$APP_DIR
Environment=DISPLAY=:99
Environment=HOME=/home/scraper
ExecStart=/bin/bash -c 'cd $APP_DIR && /home/scraper/.local/bin/poetry run python main.py'
StandardOutput=append:/var/log/scraper/scraper.log
StandardError=append:/var/log/scraper/scraper.log

# Notify on failure
ExecStopPost=/bin/bash -c 'if [ "\$EXIT_STATUS" != "0" ]; then aws sns publish --topic-arn "$SNS_TOPIC_ARN" --message "Scraper failed with exit code \$EXIT_STATUS" --subject "Scraper Error - $ENVIRONMENT" --region $AWS_REGION; fi'
EOF

# Scraper Timer (23:00 and 12:00 EST)
cat > /etc/systemd/system/scraper.timer << EOF
[Unit]
Description=Run scraper at 23:00 and 12:00 EST daily

[Timer]
# 23:00 EST = 04:00 UTC (next day)
# 12:00 EST = 17:00 UTC
OnCalendar=*-*-* 04:00:00
OnCalendar=*-*-* 17:00:00
Persistent=true
Unit=scraper.service

[Install]
WantedBy=timers.target
EOF

# MFA Service (runs permanently on port 7000)
cat > /etc/systemd/system/mfa.service << EOF
[Unit]
Description=ExpertelIQ2 MFA Authentication Service
After=network.target

[Service]
Type=simple
User=scraper
Group=scraper
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=/home/scraper/.local/bin/poetry run uvicorn mfa.main:app --host 127.0.0.1 --port 7000
Restart=always
RestartSec=5
StandardOutput=append:/var/log/scraper/mfa.log
StandardError=append:/var/log/scraper/mfa.log

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
mkdir -p /var/log/scraper
chown scraper:scraper /var/log/scraper

# Reload and enable services
systemctl daemon-reload
systemctl enable vncserver
systemctl enable websockify
systemctl enable scraper.timer
systemctl enable mfa
systemctl enable nginx

# Start services
systemctl start vncserver
sleep 5
systemctl start websockify
systemctl start mfa
systemctl start scraper.timer
systemctl start nginx

# =============================================================================
# INSTALL CLOUDWATCH AGENT
# =============================================================================

echo "Installing CloudWatch agent..."
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
dpkg -i amazon-cloudwatch-agent.deb
rm amazon-cloudwatch-agent.deb

# CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "root"
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/scraper/scraper.log",
                        "log_group_name": "/experteliq2/scraper/$ENVIRONMENT",
                        "log_stream_name": "{instance_id}/scraper",
                        "timezone": "Local"
                    },
                    {
                        "file_path": "/var/log/scraper/mfa.log",
                        "log_group_name": "/experteliq2/scraper/$ENVIRONMENT",
                        "log_stream_name": "{instance_id}/mfa",
                        "timezone": "Local"
                    },
                    {
                        "file_path": "/var/log/user-data.log",
                        "log_group_name": "/experteliq2/scraper/$ENVIRONMENT",
                        "log_stream_name": "{instance_id}/user-data",
                        "timezone": "Local"
                    }
                ]
            }
        }
    },
    "metrics": {
        "namespace": "ExpertelIQ2/Scraper",
        "metrics_collected": {
            "cpu": {
                "measurement": ["cpu_usage_active"],
                "metrics_collection_interval": 60
            },
            "mem": {
                "measurement": ["mem_used_percent"],
                "metrics_collection_interval": 60
            },
            "disk": {
                "measurement": ["disk_used_percent"],
                "metrics_collection_interval": 60,
                "resources": ["/"]
            }
        }
    }
}
EOF

systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent

# =============================================================================
# FINAL SETUP
# =============================================================================

echo "=============================================="
echo "Deployment completed!"
echo "Date: $(date)"
echo "=============================================="
echo ""
echo "Access noVNC at: https://<public-ip>/vnc/"
echo "Username: scraper"
echo "Password: (stored in SSM)"
echo ""
echo "Services:"
echo "  - MFA Service: Running on port 7000 (internal only)"
echo "  - Scraper: Runs at 23:00 EST and 12:00 EST"
echo ""
echo "Commands:"
echo "  systemctl status mfa          - Check MFA service"
echo "  systemctl status scraper.timer - Check scraper timer"
echo "  journalctl -u mfa -f          - View MFA logs"
echo "  journalctl -u scraper -f      - View scraper logs"
echo "=============================================="

# Send deployment notification
aws sns publish \
    --topic-arn "$SNS_TOPIC_ARN" \
    --message "Scraper instance deployed successfully in $ENVIRONMENT environment" \
    --subject "Scraper Deployed - $ENVIRONMENT" \
    --region $AWS_REGION || true

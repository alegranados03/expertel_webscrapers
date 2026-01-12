#!/bin/bash
# =============================================================================
# ExpertelIQ2 Scraper - Secrets Management Script
# =============================================================================
# Manages secrets in AWS SSM Parameter Store
# Usage: ./manage-secrets.sh <command> <environment>
# Commands: setup, get, set, list, validate
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APP_NAME="experteliq2-scraper"
REGION="us-east-2"

# -----------------------------------------------------------------------------
# FUNCTIONS
# -----------------------------------------------------------------------------

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed"
        echo "Install from: https://aws.amazon.com/cli/"
        exit 1
    fi

    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured"
        echo "Run: aws configure"
        exit 1
    fi
}

set_parameter() {
    local name=$1
    local value=$2
    local type=$3
    local description=$4

    aws ssm put-parameter \
        --name "$name" \
        --value "$value" \
        --type "$type" \
        --description "$description" \
        --overwrite \
        --region $REGION > /dev/null

    print_success "Set: $name"
}

get_parameter() {
    local name=$1
    aws ssm get-parameter \
        --name "$name" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text \
        --region $REGION 2>/dev/null || echo ""
}

prompt_secret() {
    local prompt=$1
    local var_name=$2
    local current_value=$3

    if [ -n "$current_value" ]; then
        echo -e "${YELLOW}Current value exists. Press Enter to keep, or type new value:${NC}"
    fi

    read -sp "$prompt: " value
    echo ""

    if [ -z "$value" ] && [ -n "$current_value" ]; then
        eval "$var_name='$current_value'"
    else
        eval "$var_name='$value'"
    fi
}

# -----------------------------------------------------------------------------
# COMMANDS
# -----------------------------------------------------------------------------

cmd_setup() {
    local env=$1
    print_header "Setting up secrets for $env environment"

    local prefix="/$APP_NAME/$env"

    # Database password
    echo ""
    echo -e "${BLUE}Database Configuration${NC}"
    current=$(get_parameter "$prefix/database/password")
    prompt_secret "PostgreSQL Password" DB_PASSWORD "$current"
    if [ -n "$DB_PASSWORD" ]; then
        set_parameter "$prefix/database/password" "$DB_PASSWORD" "SecureString" "PostgreSQL password"
    fi

    # Backend API Key
    echo ""
    echo -e "${BLUE}Backend API Configuration${NC}"
    current=$(get_parameter "$prefix/backend-api/key")
    prompt_secret "Backend API Key" API_KEY "$current"
    if [ -n "$API_KEY" ]; then
        set_parameter "$prefix/backend-api/key" "$API_KEY" "SecureString" "Backend API key"
    fi

    # Cryptography Key
    echo ""
    echo -e "${BLUE}Cryptography Configuration${NC}"
    current=$(get_parameter "$prefix/cryptography/key")
    prompt_secret "Cryptography Key" CRYPTO_KEY "$current"
    if [ -n "$CRYPTO_KEY" ]; then
        set_parameter "$prefix/cryptography/key" "$CRYPTO_KEY" "SecureString" "Cryptography key"
    fi

    # Azure Configuration
    echo ""
    echo -e "${BLUE}Azure AD Configuration${NC}"

    read -p "Azure Client ID: " AZURE_CLIENT_ID
    if [ -n "$AZURE_CLIENT_ID" ]; then
        set_parameter "$prefix/azure/client-id" "$AZURE_CLIENT_ID" "String" "Azure AD client ID"
    fi

    read -p "Azure Tenant ID: " AZURE_TENANT_ID
    if [ -n "$AZURE_TENANT_ID" ]; then
        set_parameter "$prefix/azure/tenant-id" "$AZURE_TENANT_ID" "String" "Azure AD tenant ID"
    fi

    current=$(get_parameter "$prefix/azure/client-secret")
    prompt_secret "Azure Client Secret" AZURE_SECRET "$current"
    if [ -n "$AZURE_SECRET" ]; then
        set_parameter "$prefix/azure/client-secret" "$AZURE_SECRET" "SecureString" "Azure AD client secret"
    fi

    # Anthropic API Key
    echo ""
    echo -e "${BLUE}Anthropic Configuration${NC}"
    current=$(get_parameter "$prefix/anthropic/api-key")
    prompt_secret "Anthropic API Key" ANTHROPIC_KEY "$current"
    if [ -n "$ANTHROPIC_KEY" ]; then
        set_parameter "$prefix/anthropic/api-key" "$ANTHROPIC_KEY" "SecureString" "Anthropic API key"
    fi

    # noVNC Password
    echo ""
    echo -e "${BLUE}noVNC Access Configuration${NC}"
    current=$(get_parameter "$prefix/novnc/password")
    prompt_secret "noVNC Password (for remote desktop access)" NOVNC_PASS "$current"
    if [ -n "$NOVNC_PASS" ]; then
        set_parameter "$prefix/novnc/password" "$NOVNC_PASS" "SecureString" "noVNC access password"
    fi

    # Slack Webhook
    echo ""
    echo -e "${BLUE}Notification Webhooks${NC}"
    read -p "Slack Webhook URL (or press Enter to skip): " SLACK_WEBHOOK
    if [ -n "$SLACK_WEBHOOK" ]; then
        set_parameter "$prefix/slack/webhook-url" "$SLACK_WEBHOOK" "SecureString" "Slack webhook URL"
    fi

    # Teams Webhook
    read -p "Microsoft Teams Webhook URL (or press Enter to skip): " TEAMS_WEBHOOK
    if [ -n "$TEAMS_WEBHOOK" ]; then
        set_parameter "$prefix/teams/webhook-url" "$TEAMS_WEBHOOK" "SecureString" "Teams webhook URL"
    fi

    echo ""
    print_header "Setup Complete"
    print_success "All secrets have been configured for $env environment"
}

cmd_list() {
    local env=$1
    print_header "Listing parameters for $env environment"

    local prefix="/$APP_NAME/$env"

    aws ssm get-parameters-by-path \
        --path "$prefix" \
        --recursive \
        --query 'Parameters[*].[Name,Type]' \
        --output table \
        --region $REGION
}

cmd_validate() {
    local env=$1
    print_header "Validating secrets for $env environment"

    local prefix="/$APP_NAME/$env"
    local all_valid=true

    # Required secrets
    local required_secrets=(
        "database/password"
        "backend-api/key"
        "cryptography/key"
        "azure/client-id"
        "azure/tenant-id"
        "azure/client-secret"
        "novnc/password"
    )

    # Optional secrets
    local optional_secrets=(
        "anthropic/api-key"
        "slack/webhook-url"
        "teams/webhook-url"
    )

    echo ""
    echo "Required secrets:"
    for secret in "${required_secrets[@]}"; do
        value=$(get_parameter "$prefix/$secret")
        if [ -n "$value" ]; then
            print_success "$secret"
        else
            print_error "$secret (MISSING)"
            all_valid=false
        fi
    done

    echo ""
    echo "Optional secrets:"
    for secret in "${optional_secrets[@]}"; do
        value=$(get_parameter "$prefix/$secret")
        if [ -n "$value" ]; then
            print_success "$secret"
        else
            print_warning "$secret (not set)"
        fi
    done

    echo ""
    if [ "$all_valid" = true ]; then
        print_success "All required secrets are configured"
        exit 0
    else
        print_error "Some required secrets are missing"
        exit 1
    fi
}

cmd_get() {
    local env=$1
    local param_name=$2

    if [ -z "$param_name" ]; then
        print_error "Parameter name required"
        echo "Usage: $0 get <environment> <parameter-name>"
        exit 1
    fi

    local prefix="/$APP_NAME/$env"
    value=$(get_parameter "$prefix/$param_name")

    if [ -n "$value" ]; then
        echo "$value"
    else
        print_error "Parameter not found: $prefix/$param_name"
        exit 1
    fi
}

cmd_set() {
    local env=$1
    local param_name=$2
    local param_value=$3
    local param_type=${4:-"SecureString"}

    if [ -z "$param_name" ] || [ -z "$param_value" ]; then
        print_error "Parameter name and value required"
        echo "Usage: $0 set <environment> <parameter-name> <value> [type]"
        exit 1
    fi

    local prefix="/$APP_NAME/$env"
    set_parameter "$prefix/$param_name" "$param_value" "$param_type" "Set via CLI"
}

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

show_usage() {
    echo "Usage: $0 <command> <environment> [options]"
    echo ""
    echo "Commands:"
    echo "  setup <env>              Interactive setup of all secrets"
    echo "  list <env>               List all parameters"
    echo "  validate <env>           Validate required secrets exist"
    echo "  get <env> <name>         Get a specific parameter"
    echo "  set <env> <name> <value> Set a specific parameter"
    echo ""
    echo "Environments: dev, qa, prod"
    echo ""
    echo "Examples:"
    echo "  $0 setup qa"
    echo "  $0 validate qa"
    echo "  $0 list qa"
    echo "  $0 get qa database/password"
}

# Check arguments
if [ $# -lt 2 ]; then
    show_usage
    exit 1
fi

COMMAND=$1
ENVIRONMENT=$2

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|qa|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT"
    echo "Valid environments: dev, qa, prod"
    exit 1
fi

# Check AWS CLI
check_aws_cli

# Execute command
case $COMMAND in
    setup)
        cmd_setup $ENVIRONMENT
        ;;
    list)
        cmd_list $ENVIRONMENT
        ;;
    validate)
        cmd_validate $ENVIRONMENT
        ;;
    get)
        cmd_get $ENVIRONMENT $3
        ;;
    set)
        cmd_set $ENVIRONMENT $3 $4 $5
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac

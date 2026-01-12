#Requires -Version 5.1
<#
.SYNOPSIS
    ExpertelIQ2 Scraper - Secrets Management Script for Windows

.DESCRIPTION
    Manages secrets in AWS SSM Parameter Store

.PARAMETER Command
    Command to execute: setup, list, validate, get, set

.PARAMETER Environment
    Target environment: dev, qa, prod

.EXAMPLE
    .\Manage-Secrets.ps1 -Command setup -Environment qa

.EXAMPLE
    .\Manage-Secrets.ps1 -Command validate -Environment qa
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("setup", "list", "validate", "get", "set")]
    [string]$Command,

    [Parameter(Mandatory = $true, Position = 1)]
    [ValidateSet("dev", "qa", "prod")]
    [string]$Environment,

    [Parameter(Position = 2)]
    [string]$ParamName,

    [Parameter(Position = 3)]
    [string]$ParamValue
)

# Configuration
$AppName = "experteliq2-scraper"
$Region = "us-east-2"

# Colors
function Write-Success { param([string]$Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Error { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red }
function Write-Warning { param([string]$Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Info { param([string]$Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }

# Check AWS CLI
function Test-AwsCli {
    try {
        $null = Get-Command aws -ErrorAction Stop
        $null = aws sts get-caller-identity 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Error "AWS credentials not configured. Run: aws configure"
            exit 1
        }
    }
    catch {
        Write-Error "AWS CLI is not installed"
        exit 1
    }
}

# Set parameter
function Set-SsmParameter {
    param(
        [string]$Name,
        [string]$Value,
        [string]$Type = "SecureString",
        [string]$Description = ""
    )

    aws ssm put-parameter `
        --name $Name `
        --value $Value `
        --type $Type `
        --description $Description `
        --overwrite `
        --region $Region 2>&1 | Out-Null

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Set: $Name"
    } else {
        Write-Error "Failed to set: $Name"
    }
}

# Get parameter
function Get-SsmParameter {
    param([string]$Name)

    $result = aws ssm get-parameter `
        --name $Name `
        --with-decryption `
        --query 'Parameter.Value' `
        --output text `
        --region $Region 2>&1

    if ($LASTEXITCODE -eq 0) {
        return $result
    }
    return $null
}

# Setup command
function Invoke-Setup {
    param([string]$Env)

    Write-Info "=========================================="
    Write-Info "Setting up secrets for $Env environment"
    Write-Info "=========================================="

    $prefix = "/$AppName/$Env"

    # Database password
    Write-Host ""
    Write-Info "Database Configuration"
    $dbPassword = Read-Host "PostgreSQL Password" -AsSecureString
    $dbPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword))
    if ($dbPasswordPlain) {
        Set-SsmParameter -Name "$prefix/database/password" -Value $dbPasswordPlain -Description "PostgreSQL password"
    }

    # Backend API Key
    Write-Host ""
    Write-Info "Backend API Configuration"
    $apiKey = Read-Host "Backend API Key" -AsSecureString
    $apiKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKey))
    if ($apiKeyPlain) {
        Set-SsmParameter -Name "$prefix/backend-api/key" -Value $apiKeyPlain -Description "Backend API key"
    }

    # Cryptography Key
    Write-Host ""
    Write-Info "Cryptography Configuration"
    $cryptoKey = Read-Host "Cryptography Key" -AsSecureString
    $cryptoKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($cryptoKey))
    if ($cryptoKeyPlain) {
        Set-SsmParameter -Name "$prefix/cryptography/key" -Value $cryptoKeyPlain -Description "Cryptography key"
    }

    # Azure Configuration
    Write-Host ""
    Write-Info "Azure AD Configuration"
    $azureClientId = Read-Host "Azure Client ID"
    if ($azureClientId) {
        Set-SsmParameter -Name "$prefix/azure/client-id" -Value $azureClientId -Type "String" -Description "Azure AD client ID"
    }

    $azureTenantId = Read-Host "Azure Tenant ID"
    if ($azureTenantId) {
        Set-SsmParameter -Name "$prefix/azure/tenant-id" -Value $azureTenantId -Type "String" -Description "Azure AD tenant ID"
    }

    $azureSecret = Read-Host "Azure Client Secret" -AsSecureString
    $azureSecretPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($azureSecret))
    if ($azureSecretPlain) {
        Set-SsmParameter -Name "$prefix/azure/client-secret" -Value $azureSecretPlain -Description "Azure AD client secret"
    }

    # Anthropic API Key
    Write-Host ""
    Write-Info "Anthropic Configuration"
    $anthropicKey = Read-Host "Anthropic API Key (or press Enter to skip)" -AsSecureString
    $anthropicKeyPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($anthropicKey))
    if ($anthropicKeyPlain) {
        Set-SsmParameter -Name "$prefix/anthropic/api-key" -Value $anthropicKeyPlain -Description "Anthropic API key"
    }

    # noVNC Password
    Write-Host ""
    Write-Info "noVNC Access Configuration"
    $novncPass = Read-Host "noVNC Password" -AsSecureString
    $novncPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($novncPass))
    if ($novncPassPlain) {
        Set-SsmParameter -Name "$prefix/novnc/password" -Value $novncPassPlain -Description "noVNC access password"
    }

    # Webhooks
    Write-Host ""
    Write-Info "Notification Webhooks"
    $slackWebhook = Read-Host "Slack Webhook URL (or press Enter to skip)"
    if ($slackWebhook) {
        Set-SsmParameter -Name "$prefix/slack/webhook-url" -Value $slackWebhook -Description "Slack webhook URL"
    }

    $teamsWebhook = Read-Host "Microsoft Teams Webhook URL (or press Enter to skip)"
    if ($teamsWebhook) {
        Set-SsmParameter -Name "$prefix/teams/webhook-url" -Value $teamsWebhook -Description "Teams webhook URL"
    }

    Write-Host ""
    Write-Success "Setup complete for $Env environment"
}

# List command
function Invoke-List {
    param([string]$Env)

    Write-Info "Listing parameters for $Env environment"

    $prefix = "/$AppName/$Env"

    aws ssm get-parameters-by-path `
        --path $prefix `
        --recursive `
        --query 'Parameters[*].[Name,Type]' `
        --output table `
        --region $Region
}

# Validate command
function Invoke-Validate {
    param([string]$Env)

    Write-Info "Validating secrets for $Env environment"

    $prefix = "/$AppName/$Env"
    $allValid = $true

    $requiredSecrets = @(
        "database/password",
        "backend-api/key",
        "cryptography/key",
        "azure/client-id",
        "azure/tenant-id",
        "azure/client-secret",
        "novnc/password"
    )

    $optionalSecrets = @(
        "anthropic/api-key",
        "slack/webhook-url",
        "teams/webhook-url"
    )

    Write-Host ""
    Write-Host "Required secrets:"
    foreach ($secret in $requiredSecrets) {
        $value = Get-SsmParameter -Name "$prefix/$secret"
        if ($value) {
            Write-Success $secret
        } else {
            Write-Error "$secret (MISSING)"
            $allValid = $false
        }
    }

    Write-Host ""
    Write-Host "Optional secrets:"
    foreach ($secret in $optionalSecrets) {
        $value = Get-SsmParameter -Name "$prefix/$secret"
        if ($value) {
            Write-Success $secret
        } else {
            Write-Warning "$secret (not set)"
        }
    }

    Write-Host ""
    if ($allValid) {
        Write-Success "All required secrets are configured"
    } else {
        Write-Error "Some required secrets are missing"
        exit 1
    }
}

# Get command
function Invoke-Get {
    param([string]$Env, [string]$Name)

    if (-not $Name) {
        Write-Error "Parameter name required"
        exit 1
    }

    $prefix = "/$AppName/$Env"
    $value = Get-SsmParameter -Name "$prefix/$Name"

    if ($value) {
        Write-Output $value
    } else {
        Write-Error "Parameter not found: $prefix/$Name"
        exit 1
    }
}

# Set command
function Invoke-Set {
    param([string]$Env, [string]$Name, [string]$Value)

    if (-not $Name -or -not $Value) {
        Write-Error "Parameter name and value required"
        exit 1
    }

    $prefix = "/$AppName/$Env"
    Set-SsmParameter -Name "$prefix/$Name" -Value $Value
}

# Main
Test-AwsCli

switch ($Command) {
    "setup" { Invoke-Setup -Env $Environment }
    "list" { Invoke-List -Env $Environment }
    "validate" { Invoke-Validate -Env $Environment }
    "get" { Invoke-Get -Env $Environment -Name $ParamName }
    "set" { Invoke-Set -Env $Environment -Name $ParamName -Value $ParamValue }
}

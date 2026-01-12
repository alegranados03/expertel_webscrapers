#Requires -Version 5.1
<#
.SYNOPSIS
    ExpertelIQ2 Scraper - Terraform Deployment Script for Windows

.PARAMETER Environment
    Target environment: dev, qa, prod

.PARAMETER AutoApprove
    Skip confirmation prompts

.EXAMPLE
    .\Deploy-Environment.ps1 -Environment qa

.EXAMPLE
    .\Deploy-Environment.ps1 -Environment qa -AutoApprove
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("dev", "qa", "prod")]
    [string]$Environment,

    [Parameter()]
    [switch]$AutoApprove
)

# Colors
function Write-Success { param([string]$Message) Write-Host $Message -ForegroundColor Green }
function Write-Error { param([string]$Message) Write-Host $Message -ForegroundColor Red }
function Write-Warning { param([string]$Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Info { param([string]$Message) Write-Host $Message -ForegroundColor Cyan }

Write-Info "=========================================="
Write-Info "ExpertelIQ2 Scraper - Deployment"
Write-Info "Environment: $Environment"
Write-Info "=========================================="

# Check Terraform
try {
    $null = Get-Command terraform -ErrorAction Stop
}
catch {
    Write-Error "Error: Terraform is not installed"
    exit 1
}

# Check AWS CLI
try {
    $null = Get-Command aws -ErrorAction Stop
    $null = aws sts get-caller-identity 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error: AWS credentials not configured"
        exit 1
    }
}
catch {
    Write-Error "Error: AWS CLI is not installed"
    exit 1
}

# Validate secrets first
Write-Info "Validating secrets..."
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& "$ScriptDir\Manage-Secrets.ps1" -Command validate -Environment $Environment
if ($LASTEXITCODE -ne 0) {
    Write-Error "Required secrets are missing. Run: .\Manage-Secrets.ps1 -Command setup -Environment $Environment"
    exit 1
}

# Get Terraform directory
$TerraformDir = Join-Path (Split-Path -Parent $ScriptDir) "aws\terraform\environments\$Environment"

if (-not (Test-Path $TerraformDir)) {
    Write-Error "Terraform directory not found: $TerraformDir"
    exit 1
}

Push-Location $TerraformDir

try {
    # Initialize
    Write-Info "Initializing Terraform..."
    terraform init
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform initialization failed"
        exit 1
    }

    # Plan
    Write-Host ""
    Write-Info "Planning changes..."
    terraform plan -out=tfplan
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform plan failed"
        exit 1
    }

    # Confirm
    if (-not $AutoApprove) {
        Write-Host ""
        $confirm = Read-Host "Apply these changes? (yes/no)"
        if ($confirm -ne "yes") {
            Write-Host "Deployment cancelled."
            Remove-Item -Path tfplan -ErrorAction SilentlyContinue
            exit 0
        }
    }

    # Apply
    Write-Host ""
    Write-Info "Applying changes..."
    terraform apply tfplan
    Remove-Item -Path tfplan -ErrorAction SilentlyContinue

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Success "=========================================="
        Write-Success "Deployment Complete!"
        Write-Success "=========================================="

        Write-Host ""
        Write-Info "Instance Information:"
        terraform output instance_public_ip
        terraform output novnc_url

        Write-Host ""
        Write-Info "Next Steps:"
        Write-Host "1. Wait 5-10 minutes for instance to initialize"
        Write-Host "2. Access noVNC at the URL above"
        Write-Host "3. Check timer: systemctl status scraper.timer"
    }
    else {
        Write-Error "Deployment failed"
        exit 1
    }
}
finally {
    Pop-Location
}

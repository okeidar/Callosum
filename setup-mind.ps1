<#
.SYNOPSIS
    Bootstraps the ~/mind/ wiki by copying the template directory.

.DESCRIPTION
    Copies the template/ directory from the Callosum project to ~/mind/
    and git-initializes the result. Will not overwrite an existing ~/mind/.

.EXAMPLE
    .\setup-mind.ps1
    .\setup-mind.ps1 -MindRoot "E:\mind"
#>

param(
    [string]$MindRoot = (Join-Path $env:USERPROFILE "mind")
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TemplateDir = Join-Path $ScriptDir "template"

if (-not (Test-Path $TemplateDir)) {
    Write-Error "Template directory not found at: $TemplateDir"
    exit 1
}

if (Test-Path $MindRoot) {
    Write-Host "~/mind/ already exists at: $MindRoot" -ForegroundColor Yellow
    Write-Host "To re-create, delete it first and re-run this script."
    exit 0
}

Write-Host "`n=== Callosum Mind Wiki Setup ===" -ForegroundColor Cyan
Write-Host "Source:  $TemplateDir"
Write-Host "Target:  $MindRoot`n"

# Copy template to target
Copy-Item -Path $TemplateDir -Destination $MindRoot -Recurse
Write-Host "Copied template to $MindRoot" -ForegroundColor Green

# Git init
Push-Location $MindRoot
$oldPref = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
& git init 2>&1 | Out-Null
& git add -A 2>&1 | Out-Null
& git commit -m "Phase 0: Initialize Mind Wiki structure" 2>&1 | Out-Null
$ErrorActionPreference = $oldPref
Pop-Location
Write-Host "Git initialized with initial commit" -ForegroundColor Green

# Summary
Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Mind Wiki root: $MindRoot"
Write-Host "Open in Obsidian: File > Open Vault > $MindRoot`n"

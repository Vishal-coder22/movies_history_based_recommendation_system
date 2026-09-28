#!/usr/bin/env pwsh
<# 
.SYNOPSIS
    Redeploys CineMine backend + frontend to Vercel in one command.
    Run after code changes to push updates to production.

.PREREQUISITES
    - vercel CLI installed and logged in (`vercel login`)
    - Turso DB already created/seeded (one-time only)

.USAGE
    ./deploy.ps1
#>

Set-Location -LiteralPath (Split-Path -Parent $MyInvocation.MyCommand.Definition)

Write-Host "=== Deploying backend ===" -ForegroundColor Cyan
Set-Location -LiteralPath backend
vercel --prod --yes
Set-Location ..

Write-Host "`n=== Deploying frontend ===" -ForegroundColor Cyan
Set-Location -LiteralPath frontend
vercel --prod --yes
Set-Location ..

Write-Host "`n✅ Both projects redeployed. Check Vercel dashboard for URLs." -ForegroundColor Green
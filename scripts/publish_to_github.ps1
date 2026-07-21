# Publish parade-of-trades to GitHub (run once after installing Git + gh)
# Usage (PowerShell):
#   cd C:\Users\m46d4\parade-of-trades
#   .\scripts\publish_to_github.ps1
# Optional:  .\scripts\publish_to_github.ps1 -RepoName "parade-of-trades" -Private

param(
    [string]$RepoName = "parade-of-trades",
    [switch]$Private
)

$ErrorActionPreference = "Stop"
$Git = "C:\Program Files\Git\bin\git.exe"
$Gh = "$env:ProgramFiles\GitHub CLI\gh.exe"
if (-not (Test-Path $Gh)) {
    $Gh = "$env:LOCALAPPDATA\Programs\GitHub CLI\gh.exe"
}
if (-not (Test-Path $Git)) { throw "Git not found. Install from https://git-scm.com" }
if (-not (Test-Path $Gh)) { throw "GitHub CLI not found. Install: winget install GitHub.cli" }

Set-Location (Split-Path $PSScriptRoot -Parent)

# Ensure auth
& $Gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Login ke GitHub (browser akan terbuka)..." -ForegroundColor Yellow
    & $Gh auth login -p https -w
}

$visibility = if ($Private) { "--private" } else { "--public" }
Write-Host "Membuat repo GitHub: $RepoName ($visibility) dan push..." -ForegroundColor Cyan

& $Gh repo create $RepoName $visibility --source=. --remote=origin --push --description "Parade of Trades - Lean Construction simulation (Streamlit)"

if ($LASTEXITCODE -eq 0) {
    $url = & $Gh repo view --json url -q .url
    Write-Host ""
    Write-Host "SUKSES. Repo: $url" -ForegroundColor Green
    Write-Host "Lanjut deploy: https://share.streamlit.io  → New app → pilih repo ini → Main file: app.py" -ForegroundColor Green
} else {
    Write-Host "Gagal. Jika remote origin sudah ada, coba: git push -u origin main" -ForegroundColor Red
}

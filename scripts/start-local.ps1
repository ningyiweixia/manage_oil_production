param(
    [switch]$Foreground
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$logsDir = Join-Path $repoRoot ".local\logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

if ($Foreground) {
    Write-Host "Starting backend in this PowerShell window. Open another window for scripts/start-local-frontend.ps1." -ForegroundColor Yellow
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "scripts\start-local-backend.ps1")
    exit $LASTEXITCODE
}

$backendScript = Join-Path $repoRoot "scripts\start-local-backend.ps1"
$frontendScript = Join-Path $repoRoot "scripts\start-local-frontend.ps1"

cmd.exe /c "start ""manage-factory-backend"" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""$backendScript"""
cmd.exe /c "start ""manage-factory-frontend"" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""$frontendScript"""

Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://127.0.0.1:5173" -ForegroundColor Cyan
Write-Host "Docs:     http://127.0.0.1:8000/docs" -ForegroundColor Cyan

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$dbPath = Join-Path $repoRoot "local_dev.db"
$backupDir = Join-Path $repoRoot "backups"

if (-not (Test-Path $dbPath)) {
    throw "Local database not found: $dbPath"
}

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $backupDir "local_dev-$stamp.db"
Copy-Item -LiteralPath $dbPath -Destination $target -Force

Write-Host "Backup created: $target"

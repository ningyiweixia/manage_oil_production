param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$dbPath = Join-Path $repoRoot "local_dev.db"
$source = Resolve-Path $BackupPath

Copy-Item -LiteralPath $source -Destination $dbPath -Force
Write-Host "Database restored from: $source"

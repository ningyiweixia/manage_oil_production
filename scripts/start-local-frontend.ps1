Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$frontendRoot = Join-Path $repoRoot "frontend"
Set-Location $frontendRoot

if ($env:SKIP_FRONTEND_INSTALL -ne "1" -and -not (Test-Path (Join-Path $frontendRoot "node_modules"))) {
    npm install
}

$port = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "5173" }
npm run dev -- --host 127.0.0.1 --port $port

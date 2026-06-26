Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$env:POSTGRES_PASSWORD = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "local-check-postgres-password" }
$env:JWT_SECRET_KEY = if ($env:JWT_SECRET_KEY) { $env:JWT_SECRET_KEY } else { "local-check-jwt-secret" }

python -m compileall app main.py celery_app.py
python -m unittest discover -s tests -v

Push-Location frontend
try {
    npm run build
}
finally {
    Pop-Location
}

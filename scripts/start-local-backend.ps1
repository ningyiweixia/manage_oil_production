Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $python = (Get-Command py -ErrorAction SilentlyContinue)
    if ($python) {
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            & py -3 -m venv .venv
        }
    }
    else {
        & python -m venv .venv
    }
}

if ($env:SKIP_BACKEND_INSTALL -ne "1") {
    & $venvPython -m pip install -r requirements.txt
}

$env:DATABASE_URL = if ($env:DATABASE_URL) { $env:DATABASE_URL } else { "sqlite:///./local_dev.db" }
$env:POSTGRES_PASSWORD = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "local-dev-postgres-placeholder" }
$env:JWT_SECRET_KEY = if ($env:JWT_SECRET_KEY) { $env:JWT_SECRET_KEY } else { "local-dev-jwt-secret-change-me" }
$env:ADMIN_INITIAL_PASSWORD = if ($env:ADMIN_INITIAL_PASSWORD) { $env:ADMIN_INITIAL_PASSWORD } else { "ChangeMe_123!" }
$env:CORS_ALLOW_ORIGINS = if ($env:CORS_ALLOW_ORIGINS) { $env:CORS_ALLOW_ORIGINS } else { "http://127.0.0.1:5173,http://localhost:5173" }
$env:REDIS_URL = if ($env:REDIS_URL) { $env:REDIS_URL } else { "" }

@"
from app import models  # noqa: F401
from app.db.base import Base
from app.db.session import engine
from app.db.local_schema import ensure_sqlite_columns
from app.db.seed import seed

Base.metadata.create_all(bind=engine)
ensure_sqlite_columns(engine)
seed()
print("Local database initialized")
"@ | & $venvPython -

& $venvPython -m uvicorn main:app --host 127.0.0.1 --port 8000

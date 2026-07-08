# Local Startup Log

## 2026-07-08 PostgreSQL local startup method on macOS

This repository now includes a tracked helper for the local PostgreSQL workflow:

```bash
./scripts/start-local-postgres.sh
```

What it does:
- creates `.venv` with Python 3.12 when available
- installs backend dependencies from `requirements.txt`
- installs frontend dependencies when `frontend/node_modules` is missing
- creates the local PostgreSQL database when missing
- runs `alembic upgrade head`
- seeds menus, roles, permissions, dictionaries, and the default admin user
- starts backend on `http://127.0.0.1:8000`
- starts frontend on `http://127.0.0.1:5173`

Default PostgreSQL connection:

```text
host: 127.0.0.1
port: 5432
user: current OS user
database: manage_factory
password: empty
```

Override with environment variables when needed:

```bash
POSTGRES_USER=postgres POSTGRES_PASSWORD=your-password ./scripts/start-local-postgres.sh
```

Stop processes started by the helper:

```bash
./scripts/stop-local.sh
```

Verified URLs:
- Backend: `http://127.0.0.1:8000`
- Backend health: `http://127.0.0.1:8000/health`
- Backend docs: `http://127.0.0.1:8000/docs`
- Frontend: `http://127.0.0.1:5173`

Verified account:
- Username: `admin`
- Password: `ChangeMe_123!`

## 2026-06-29 verified startup method

This project should prefer the following local startup method on Windows.

Reason:
- `Start-Process` failed in this environment because duplicated environment keys such as `Path` and `PATH` caused a PowerShell dictionary conflict.
- Direct foreground execution of the `.local` startup scripts worked.
- `cmd.exe /c start ... /min ...` successfully started both services as minimized local development processes.
- Backend health check, frontend page load, frontend proxy, and admin login were verified.

Verified URLs:
- Backend: `http://127.0.0.1:8000`
- Backend health: `http://127.0.0.1:8000/health`
- Backend docs: `http://127.0.0.1:8000/docs`
- Frontend: `http://127.0.0.1:5173`

Verified account:
- Username: `admin`
- Password: `ChangeMe_123!`

## Preferred manual startup

Open PowerShell and enter the project root:

```powershell
cd D:\workspace\githubprojects\oil_production\manage_oil_production
```

Initialize or refresh the local SQLite database when needed:

```powershell
$env:DATABASE_URL="sqlite:///./local_dev.db"
$env:POSTGRES_PASSWORD="local-dev-postgres-placeholder"
$env:JWT_SECRET_KEY="local-dev-jwt-secret-change-me"
$env:ADMIN_INITIAL_PASSWORD="ChangeMe_123!"
$env:CORS_ALLOW_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"
$env:REDIS_URL=""

@'
from app import models
from app.db.base import Base
from app.db.session import engine
from app.db.seed import seed

Base.metadata.create_all(bind=engine)
seed()
print("Local database initialized")
'@ | .\.venv\Scripts\python.exe -
```

Start backend in the foreground:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\.local\start-backend.ps1
```

Start frontend in another PowerShell window:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\.local\start-frontend.ps1
```

## Preferred minimized startup

From PowerShell:

```powershell
cmd.exe /c 'start "oil-backend" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\workspace\githubprojects\oil_production\manage_oil_production\.local\start-backend.ps1"'
```

```powershell
cmd.exe /c 'start "oil-frontend" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\workspace\githubprojects\oil_production\manage_oil_production\.local\start-frontend.ps1"'
```

Use the single-quoted `cmd.exe /c 'start "title" ...'` form from PowerShell. It preserves the quoted window title for `cmd start`; without that, Windows may treat `oil-backend` or `oil-frontend` as the file to open.

## Local helper scripts

The successful startup used these local helper scripts:
- `D:\workspace\githubprojects\oil_production\manage_oil_production\.local\start-backend.ps1`
- `D:\workspace\githubprojects\oil_production\manage_oil_production\.local\start-frontend.ps1`

These files are intentionally under `.local/`, which is ignored by git. If they are missing, recreate them with the contents below.

Backend helper:

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$env:DATABASE_URL = if ($env:DATABASE_URL) { $env:DATABASE_URL } else { "sqlite:///./local_dev.db" }
$env:POSTGRES_PASSWORD = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "local-dev-postgres-placeholder" }
$env:JWT_SECRET_KEY = if ($env:JWT_SECRET_KEY) { $env:JWT_SECRET_KEY } else { "local-dev-jwt-secret-change-me" }
$env:ADMIN_INITIAL_PASSWORD = if ($env:ADMIN_INITIAL_PASSWORD) { $env:ADMIN_INITIAL_PASSWORD } else { "ChangeMe_123!" }
$env:CORS_ALLOW_ORIGINS = if ($env:CORS_ALLOW_ORIGINS) { $env:CORS_ALLOW_ORIGINS } else { "http://127.0.0.1:5173,http://localhost:5173" }
$env:REDIS_URL = if ($env:REDIS_URL) { $env:REDIS_URL } else { "" }

Start-Transcript -Path (Join-Path $repoRoot ".local\logs\backend.transcript.log") -Force
try {
    & (Join-Path $repoRoot ".venv\Scripts\python.exe") -m uvicorn main:app --host 127.0.0.1 --port 8000
}
finally {
    Stop-Transcript
}
```

Frontend helper:

```powershell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$frontendRoot = Join-Path $repoRoot "frontend"
Set-Location $frontendRoot

Start-Transcript -Path (Join-Path $repoRoot ".local\logs\frontend.transcript.log") -Force
try {
    & "C:\Program Files\nodejs\npm.cmd" run dev -- --host 127.0.0.1 --port 5173
}
finally {
    Stop-Transcript
}
```

## Verification commands

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing -TimeoutSec 10
Invoke-WebRequest -Uri http://127.0.0.1:8000/docs -UseBasicParsing -TimeoutSec 10
Invoke-WebRequest -Uri http://127.0.0.1:5173 -UseBasicParsing -TimeoutSec 10
Invoke-WebRequest -Uri http://127.0.0.1:5173/api/v1/auth/login -Method Options -UseBasicParsing -TimeoutSec 10
```

Log files:
- `D:\workspace\githubprojects\oil_production\manage_oil_production\.local\logs\backend.transcript.log`
- `D:\workspace\githubprojects\oil_production\manage_oil_production\.local\logs\frontend.transcript.log`

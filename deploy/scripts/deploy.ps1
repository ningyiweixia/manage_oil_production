param(
    [switch]$SkipBuild,
    [switch]$SkipMigrate
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Review secrets before production use."
}

New-Item -ItemType Directory -Force "logs\nginx","logs\backend","logs\postgres","deploy\nginx\ssl" | Out-Null

$CertPath = "deploy\nginx\ssl\server.crt"
$KeyPath = "deploy\nginx\ssl\server.key"
if (-not (Test-Path $CertPath) -or -not (Test-Path $KeyPath)) {
    $openssl = Get-Command openssl -ErrorAction SilentlyContinue
    if (-not $openssl) {
        throw "OpenSSL is required to generate the initial TLS certificate. Install OpenSSL or place server.crt/server.key in deploy/nginx/ssl."
    }
    $OpenSslConfig = Join-Path $env:TEMP "manage_factory_openssl.cnf"
    @"
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = CN
O = Oilfield Internal
CN = manage-factory.internal

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = manage-factory.internal
DNS.2 = localhost
IP.1 = 127.0.0.1
"@ | Set-Content -Path $OpenSslConfig -Encoding ascii

    Invoke-Checked -Name "TLS certificate generation" -Command {
        & openssl req -x509 -nodes -newkey rsa:4096 -days 3650 `
            -keyout $KeyPath `
            -out $CertPath `
            -config $OpenSslConfig
    }
}

$composeArgs = @("compose", "-f", "docker-compose.yml")
if ($SkipBuild) {
    Invoke-Checked -Name "docker compose up" -Command { & docker @composeArgs up -d }
} else {
    Invoke-Checked -Name "docker compose up --build" -Command { & docker @composeArgs up -d --build }
}

if (-not $SkipMigrate) {
    Invoke-Checked -Name "alembic migration" -Command { & docker @composeArgs exec -T backend alembic upgrade head }
    Invoke-Checked -Name "seed initialization" -Command { & docker @composeArgs exec -T backend python -m app.db.seed }
}

Invoke-Checked -Name "docker compose ps" -Command { & docker @composeArgs ps }
Write-Host ""
Write-Host "DMZ HTTPS entry: https://localhost/"
Write-Host "Grafana: https://localhost/grafana/"
Write-Host "Backend health: https://localhost/health"

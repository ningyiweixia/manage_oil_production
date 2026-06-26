Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$outputPath = Join-Path $repoRoot "runtime-dashboard.html"
$generatedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function HtmlEscape {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) {
        return ""
    }
    return [System.Net.WebUtility]::HtmlEncode([string]$Value)
}

function New-CheckResult {
    param(
        [string]$Name,
        [string]$State,
        [string]$Summary,
        [string]$Detail,
        [string]$Body = ""
    )

    return [pscustomobject]@{
        Name = $Name
        State = $State
        Summary = $Summary
        Detail = $Detail
        Body = $Body
    }
}

function Redact-LoginBody {
    param([string]$Body)

    try {
        $parsed = $Body | ConvertFrom-Json
        if ($parsed.code -eq 20000 -and $parsed.data) {
            $username = $parsed.data.user.username
            $permissionCount = @($parsed.data.permissions).Count
            $menuCount = @($parsed.data.menus).Count
            return (@{
                code = $parsed.code
                msg = $parsed.msg
                data = @{
                    user = @{ username = $username }
                    token = "[redacted]"
                    permission_count = $permissionCount
                    menu_count = $menuCount
                }
            } | ConvertTo-Json -Compress -Depth 5)
        }
    }
    catch {
        return $Body
    }

    return $Body
}

function Test-Port {
    param(
        [string]$Name,
        [int]$Port,
        [string]$Description
    )

    $connection = Test-NetConnection 127.0.0.1 -Port $Port -WarningAction SilentlyContinue
    if ($connection.TcpTestSucceeded) {
        return New-CheckResult $Name "ok" "127.0.0.1:$Port reachable" $Description
    }

    return New-CheckResult $Name "down" "127.0.0.1:$Port unreachable" $Description
}

function Test-Http {
    param(
        [string]$Name,
        [string]$Uri,
        [string]$Description
    )

    try {
        $response = Invoke-WebRequest -Uri $Uri -TimeoutSec 5
        return New-CheckResult $Name "ok" "HTTP $($response.StatusCode)" $Description $response.Content
    }
    catch {
        $status = "No response"
        $body = $_.Exception.Message
        if ($_.Exception.Response) {
            $status = "HTTP $([int]$_.Exception.Response.StatusCode)"
            try {
                $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
                $body = $reader.ReadToEnd()
                $reader.Close()
            }
            catch {
                $body = $_.Exception.Message
            }
        }
        return New-CheckResult $Name "down" $status $Description $body
    }
}

function Test-Login {
    $payload = @{ username = "admin"; password = "ChangeMe_123!" } | ConvertTo-Json -Compress
    $targets = @(
        "http://127.0.0.1:5173/api/v1/auth/login",
        "http://127.0.0.1:8000/api/v1/auth/login"
    )

    foreach ($target in $targets) {
        try {
            $response = Invoke-WebRequest -Method Post -Uri $target -ContentType "application/json" -Body $payload -TimeoutSec 8
            return New-CheckResult "Login API" "ok" "HTTP $($response.StatusCode)" "POST /api/v1/auth/login via $target" (Redact-LoginBody $response.Content)
        }
        catch {
            if ($_.Exception.Response) {
                $statusCode = [int]$_.Exception.Response.StatusCode
                $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
                $body = $reader.ReadToEnd()
                $reader.Close()
                $state = if ($statusCode -eq 503) { "warn" } else { "down" }
                return New-CheckResult "Login API" $state "HTTP $statusCode" "POST /api/v1/auth/login via $target" $body
            }
        }
    }

    return New-CheckResult "Login API" "down" "No response" "POST /api/v1/auth/login" "Both frontend proxy and backend login endpoint are unavailable."
}

$checks = @(
    (Test-Http "Backend health" "http://127.0.0.1:8000/health" "FastAPI /health"),
    (Test-Http "Frontend page" "http://127.0.0.1:5173/" "Vite dev server"),
    (Test-Port "PostgreSQL" 5432 "Primary business database"),
    (Test-Port "Redis" 6379 "Cache, token revocation, async task broker"),
    (Test-Login)
)

$okCount = @($checks | Where-Object { $_.State -eq "ok" }).Count
$warnCount = @($checks | Where-Object { $_.State -eq "warn" }).Count
$downCount = @($checks | Where-Object { $_.State -eq "down" }).Count

$cards = foreach ($check in $checks) {
@"
      <article class="card $($check.State)">
        <div class="card-head">
          <span class="dot"></span>
          <h2>$(HtmlEscape $check.Name)</h2>
        </div>
        <p class="summary">$(HtmlEscape $check.Summary)</p>
        <p class="detail">$(HtmlEscape $check.Detail)</p>
        <pre>$(HtmlEscape $check.Body)</pre>
      </article>
"@
}

$html = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Runtime Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #667085;
      --line: #d8dee8;
      --ok: #168a4a;
      --warn: #b7791f;
      --down: #c0392b;
      --paper: #f6f8fb;
      --panel: #ffffff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: var(--paper);
      color: var(--ink);
    }
    header {
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 { margin: 0 0 8px; font-size: 26px; font-weight: 700; }
    .meta { margin: 0; color: var(--muted); font-size: 14px; }
    .scoreboard {
      display: grid;
      grid-template-columns: repeat(3, minmax(120px, 1fr));
      gap: 12px;
      padding: 18px 32px 4px;
      max-width: 960px;
    }
    .metric {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px 16px;
    }
    .metric strong { display: block; font-size: 24px; }
    .metric span { color: var(--muted); font-size: 13px; }
    main {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
      padding: 18px 32px 32px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-left-width: 6px;
      border-radius: 8px;
      min-height: 190px;
      padding: 16px;
    }
    .card.ok { border-left-color: var(--ok); }
    .card.warn { border-left-color: var(--warn); }
    .card.down { border-left-color: var(--down); }
    .card-head { display: flex; align-items: center; gap: 10px; }
    .card h2 { margin: 0; font-size: 18px; }
    .dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--down);
      flex: 0 0 auto;
    }
    .ok .dot { background: var(--ok); }
    .warn .dot { background: var(--warn); }
    .summary { margin: 14px 0 6px; font-size: 16px; font-weight: 600; }
    .detail { margin: 0 0 12px; color: var(--muted); line-height: 1.5; }
    pre {
      margin: 0;
      padding: 10px;
      max-height: 140px;
      overflow: auto;
      border-radius: 6px;
      background: #f0f3f7;
      color: #27384a;
      font-size: 12px;
      white-space: pre-wrap;
      word-break: break-word;
    }
  </style>
</head>
<body>
  <header>
    <h1>Runtime Dashboard</h1>
    <p class="meta">Generated at: $generatedAt; repository: $(HtmlEscape $repoRoot)</p>
  </header>
  <section class="scoreboard" aria-label="Runtime summary">
    <div class="metric"><strong>$okCount</strong><span>OK</span></div>
    <div class="metric"><strong>$warnCount</strong><span>Expected degraded</span></div>
    <div class="metric"><strong>$downCount</strong><span>Unavailable</span></div>
  </section>
  <main>
$($cards -join "`n")
  </main>
</body>
</html>
"@

[System.IO.File]::WriteAllText($outputPath, $html, [System.Text.UTF8Encoding]::new($false))
Write-Output $outputPath

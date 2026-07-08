Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Backend = if ($env:BACKEND_URL) { $env:BACKEND_URL } else { "http://127.0.0.1:8000" }
$Frontend = if ($env:FRONTEND_URL) { $env:FRONTEND_URL } else { "http://127.0.0.1:5173" }
$Username = if ($env:DEMO_USERNAME) { $env:DEMO_USERNAME } else { "admin" }
$Password = if ($env:DEMO_PASSWORD) { $env:DEMO_PASSWORD } else { "ChangeMe_123!" }

function Assert-HttpOk {
    param(
        [string]$Name,
        [string]$Uri,
        [hashtable]$Headers = @{}
    )
    $response = Invoke-WebRequest -Uri $Uri -Headers $Headers -TimeoutSec 10
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 300) {
        throw "$Name failed with HTTP $($response.StatusCode)"
    }
    Write-Host "[OK] $Name"
    return $response
}

Assert-HttpOk "Backend health" "$Backend/health" | Out-Null
Assert-HttpOk "Frontend page" "$Frontend/" | Out-Null

$loginBody = @{ username = $Username; password = $Password } | ConvertTo-Json -Compress
$login = Invoke-WebRequest -Method Post -Uri "$Backend/api/v1/auth/login" -ContentType "application/json" -Body $loginBody -TimeoutSec 10
$loginPayload = $login.Content | ConvertFrom-Json
if ($loginPayload.code -ne 20000) {
    throw "Login failed: $($loginPayload.msg)"
}
$token = $loginPayload.data.token.access_token
$headers = @{ Authorization = "Bearer $token" }
Write-Host "[OK] Login as $Username"

$checks = @(
    @{ Name = "Project pool"; Uri = "$Backend/api/v1/workover-project-pools/?page=1&page_size=5" },
    @{ Name = "Approval logs"; Uri = "$Backend/api/v1/approval-logs?limit=5" },
    @{ Name = "Operation sheets"; Uri = "$Backend/api/v1/contractors/operation-sheets/?page=1&page_size=5" },
    @{ Name = "Operation analytics"; Uri = "$Backend/api/v1/contractors/analytics/summary" },
    @{ Name = "Material requirements"; Uri = "$Backend/api/v1/materials/?page=1&page_size=5" },
    @{ Name = "Completion ledger"; Uri = "$Backend/api/v1/well-completions/?page=1&page_size=5" },
    @{ Name = "Delivery summary"; Uri = "$Backend/api/v1/reports/delivery-summary" },
    @{ Name = "Operation logs"; Uri = "$Backend/api/v1/operation-logs?page=1&page_size=5" }
)

foreach ($check in $checks) {
    $response = Assert-HttpOk $check.Name $check.Uri $headers
    $payload = $response.Content | ConvertFrom-Json
    if ($payload.code -ne 20000) {
        throw "$($check.Name) business response failed: $($payload.msg)"
    }
}

Assert-HttpOk "Excel report" "$Backend/api/v1/reports/delivery-summary.xlsx" $headers | Out-Null
Assert-HttpOk "Word report" "$Backend/api/v1/reports/delivery-summary.docx" $headers | Out-Null

Write-Host "Acceptance check completed."

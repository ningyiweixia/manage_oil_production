param(
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw "Please run this script from an elevated PowerShell session."
}

Write-Host "Enabling Windows Subsystem for Linux..."
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

Write-Host "Enabling Virtual Machine Platform..."
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

Write-Host "Setting WSL2 as default when WSL becomes available..."
try {
    wsl --set-default-version 2
} catch {
    Write-Host "WSL default version will be finalized after restart."
}

Write-Host ""
Write-Host "WSL2 prerequisites are enabled. A Windows restart is usually required before Docker Desktop can start."
if (-not $NoRestart) {
    Write-Host "Restart this machine now, then reopen this project and run: docker compose -f docker-compose.yml config"
}

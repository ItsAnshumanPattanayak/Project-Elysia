$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Backend environment is missing. Run scripts\setup.ps1 first." }

$HostAddress = if ($env:API_HOST) { $env:API_HOST } else { "127.0.0.1" }
$Port = if ($env:API_PORT) { $env:API_PORT } else { "8000" }
Write-Host "Starting Project Elysia API at http://${HostAddress}:${Port}"
Push-Location $Backend
try { & $Python -m uvicorn app.main:app --reload --host $HostAddress --port $Port } finally { Pop-Location }

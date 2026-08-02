$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Frontend = Join-Path $Root "frontend"
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) { throw "Frontend dependencies are missing. Run scripts\setup.ps1 first." }
Write-Host "Starting Project Elysia frontend at http://localhost:5173"
Push-Location $Frontend
try { npm.cmd run dev } finally { Pop-Location }

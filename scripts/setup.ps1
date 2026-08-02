$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python 3.11 or newer is required." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js is required." }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "npm is required." }

if (-not (Test-Path $VenvPython)) { python -m venv (Join-Path $Backend ".venv") }
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $Backend "requirements-dev.txt")
Push-Location $Frontend
try { npm.cmd install } finally { Pop-Location }

foreach ($Area in @($Backend, $Frontend)) {
    $Example = Join-Path $Area ".env.example"
    $Environment = Join-Path $Area ".env"
    if (-not (Test-Path $Environment)) { Copy-Item -LiteralPath $Example -Destination $Environment }
}

Push-Location $Backend
try { & $VenvPython -m alembic upgrade head; & $VenvPython scripts\init_db.py } finally { Pop-Location }
Write-Host "Setup complete. Run scripts\start_backend.ps1 and scripts\start_frontend.ps1."

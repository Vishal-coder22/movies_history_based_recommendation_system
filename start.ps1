# Starts CineMine: backend (uvicorn) + frontend (vite) in one window.
#   .\start.ps1          both servers
#   .\start.ps1 -Backend  backend only (http://127.0.0.1:8000)
#   .\start.ps1 -Frontend frontend only (http://localhost:5173)
param([switch]$Backend, [switch]$Frontend)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$both = -not ($Backend -or $Frontend)
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment not found at $venvPython. Run: python -m venv .venv && .venv\Scripts\pip install -r backend\requirements.txt"
    exit 1
}

$jobs = @()

if ($both -or $Backend) {
    $jobs += Start-Process -FilePath $venvPython `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000" `
        -WorkingDirectory (Join-Path $root "backend") `
        -PassThru -WindowStyle Normal
    Write-Host "Backend:  http://127.0.0.1:8000  (docs at /docs)"
}

if ($both -or $Frontend) {
    Push-Location (Join-Path $root "frontend")
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing frontend dependencies (first run)..."
        npm install
    }
    $jobs += Start-Process -FilePath "npm.cmd" `
        -ArgumentList "run", "dev" `
        -WorkingDirectory (Join-Path $root "frontend") `
        -PassThru -WindowStyle Normal
    Pop-Location
    Write-Host "Frontend: http://localhost:5173"
}

Write-Host ""
Write-Host "Press Ctrl+C in each server window to stop. Close this window to leave both running."
$jobs | ForEach-Object { Write-Host "  pid $($_.Id)" }

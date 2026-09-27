# Runs the backend test suite. Safe from any working directory:
#   .\test.ps1        fast suite (default)
#   .\test.ps1 -All   everything, including tests marked "slow"
param([switch]$All)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment not found at $venvPython. Run: python -m venv .venv"
    exit 1
}

$markerArgs = if ($All) { @() } else { @('-m', 'not slow') }
& $venvPython -m pytest @markerArgs @args
exit $LASTEXITCODE

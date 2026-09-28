# Runs the backend test suite. Safe from any working directory:
#   .\test.ps1        fast suite (default)
#   .\test.ps1 -All   everything, including tests marked "slow"
param([switch]$All)

$markerArgs = if ($All) { @() } else { @('-m', 'not slow') }
python -m pytest -n auto @markerArgs @args
exit $LASTEXITCODE

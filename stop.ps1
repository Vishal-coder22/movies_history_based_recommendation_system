# Stops every CineMine server (backend + frontend).
#   .\stop.ps1
# Works from any folder. Safe to run when nothing is running.
$ErrorActionPreference = 'SilentlyContinue'

$root   = Split-Path -Parent $MyInvocation.MyCommand.Path
$marker = Join-Path $root 'logs\stop-requested'
$ports  = 5173, 5174, 5175, 8000
$found  = $false

# 0) Flag the stop as intentional FIRST, so a running start.ps1 window
#    reports "Stopped by .\stop.ps1" instead of a crash.
New-Item -ItemType File -Force -Path $marker | Out-Null

# 1) Anything listening on our ports (backend or vite).
foreach ($port in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in @($conns)) {
        $found = $true
        $name = (Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue).ProcessName
        & taskkill.exe /PID $conn.OwningProcess /T /F 2>&1 | Out-Null
        Write-Host "  [..] stopped '$name' (pid $($conn.OwningProcess)) on port $port"
    }
}

# 2) Orphans that are starting up (not bound to a port yet) from this project.
$self = $PID
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessId -ne $self -and $_.CommandLine -and (
        ($_.CommandLine -like "*$root*uvicorn*") -or
        ($_.CommandLine -like "*$root*app.main:app*") -or
        ($_.CommandLine -like "*$root*frontend*vite*")
    )
} | ForEach-Object {
    $found = $true
    & taskkill.exe /PID $_.ProcessId /T /F 2>&1 | Out-Null
    Write-Host "  [..] stopped '$($_.Name)' (pid $($_.ProcessId))"
}

if ($found) { Start-Sleep -Milliseconds 1000 }

# 3) Verify the ports are really free.
$busy = @()
foreach ($port in 5173, 8000) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        $busy += $port
    }
}

Write-Host ''
if (-not $found) {
    Write-Host '  Nothing to stop - no CineMine servers are running.' -ForegroundColor DarkGray
} elseif ($busy.Count -eq 0) {
    Write-Host '  [OK] All CineMine servers stopped - ports 5173 and 8000 are free.' -ForegroundColor Green
} else {
    Write-Host "  [!!] Still busy: $($busy -join ', ') - close any window still running the server." -ForegroundColor Red
    exit 1
}
Write-Host '  Start again with:  .\start.ps1'
Write-Host ''
exit 0

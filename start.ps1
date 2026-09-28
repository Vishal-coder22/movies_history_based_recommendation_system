# CineMine launcher - runs backend + frontend in ONE window.
#
#   .\start.ps1             start both servers (recommended)
#   .\start.ps1 -Backend    backend only  (http://127.0.0.1:8000)
#   .\start.ps1 -Frontend   frontend only (http://localhost:5173)
#
# Works from any folder. Press ENTER in this window to stop both servers.
param([switch]$Backend, [switch]$Frontend)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$root        = Split-Path -Parent $MyInvocation.MyCommand.Path
$startB      = $Backend -or (-not ($Backend -or $Frontend))
$startF      = $Frontend -or (-not ($Backend -or $Frontend))
$venvPython  = "python"
$backendDir  = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'
$logDir      = Join-Path $root 'logs'
$marker      = Join-Path $logDir 'stop-requested'

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Remove-Item $marker -ErrorAction SilentlyContinue
$stopRequested = $false

function Fail([string]$Title, [string[]]$Lines) {
    Write-Host ''
    Write-Host "  [FAIL] $Title" -ForegroundColor Red
    foreach ($line in $Lines) { Write-Host "         $line" -ForegroundColor DarkGray }
    Read-Host '  Press Enter to close this window'
    exit 1
}

# Returns @{ Up = bool; Body = string } - any HTTP answer counts as "up".
function Wait-Endpoint([string]$Url, [int]$MaxSeconds) {
    $deadline = (Get-Date).AddSeconds($MaxSeconds)
    $dots = 0
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            return @{ Up = $true; Body = $r.Content }
        } catch {
            if ($_.Exception.Response) { return @{ Up = $true; Body = $null } }
            if ($dots -lt 30) { Write-Host -NoNewline '.'; $dots++ }
            Start-Sleep -Milliseconds 900
        }
    }
    return @{ Up = $false; Body = $null }
}

function Free-Port([int]$Port) {
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in @($conns)) {
        $name = (Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue).ProcessName
        & taskkill.exe /PID $c.OwningProcess /T /F 2>&1 | Out-Null
        Write-Host "  [..] stopped old '$name' (pid $($c.OwningProcess)) using port $Port" -ForegroundColor DarkYellow
    }
    if ($conns) { Start-Sleep -Milliseconds 800 }
}

function Stop-Tree($Proc) {
    if ($Proc -and -not $Proc.HasExited) {
        & taskkill.exe /PID $Proc.Id /T /F 2>&1 | Out-Null
    }
}

# Show only NEW lines from a log file (prefix so you know who said it).
function Show-New([hashtable]$Log) {
    if (-not (Test-Path -LiteralPath $Log.Path)) { return }
    $lines = @(Get-Content -LiteralPath $Log.Path -ErrorAction SilentlyContinue)
    if ($lines.Count -gt $Log.Seen) {
        for ($i = $Log.Seen; $i -lt $lines.Count; $i++) {
            Write-Host ("  [{0}] {1}" -f $Log.Name, $lines[$i]) -ForegroundColor DarkGray
        }
        $Log.Seen = $lines.Count
    }
}

Write-Host ''
Write-Host '  CineMine launcher' -ForegroundColor Yellow
Write-Host "  Project: $root"
Write-Host ''

# ---- preflight ----------------------------------------------------------
if ($startB -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    Fail 'Python not found in PATH.' @(
        'Install Python 3.12+ and ensure it is in your PATH.'
    )
}
if ($startB) {
    if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
        Write-Host '  [..] Port 8000 is busy - stopping the old server first' -ForegroundColor DarkYellow
        Free-Port 8000
    }
}
if ($startF) {
    foreach ($p in 5173, 5174, 5175) {
        if (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) { Free-Port $p }
    }
    if (-not (Test-Path (Join-Path $frontendDir 'node_modules'))) {
        Write-Host '  [..] Installing frontend dependencies (first run, one time only)...' -ForegroundColor DarkYellow
        Push-Location $frontendDir
        npm install
        Pop-Location
    }
}

$backendOut  = Join-Path $logDir 'backend.out.log'
$backendErr  = Join-Path $logDir 'backend.err.log'
$frontendOut = Join-Path $logDir 'frontend.out.log'
$frontendErr = Join-Path $logDir 'frontend.err.log'
Remove-Item $backendOut, $backendErr, $frontendOut, $frontendErr -ErrorAction SilentlyContinue

$backendProc = $null
$frontendProc = $null

# ---- start backend ------------------------------------------------------
if ($startB) {
    Write-Host -NoNewline '  [1/2] Starting backend'
    try {
        $backendProc = Start-Process -FilePath $venvPython `
            -ArgumentList '-m', 'uvicorn', 'app.main:app', '--port', '8000', '--no-access-log' `
            -WorkingDirectory $backendDir `
            -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr `
            -PassThru
    } catch {
        Fail 'Could not start the backend.' @("$($_.Exception.Message)", "Folder: $backendDir", "$($_.ScriptStackTrace)")
    }

    $health = Wait-Endpoint 'http://127.0.0.1:8000/api/health' 60
    Write-Host ''
    if (-not $health.Up) {
        Stop-Tree $backend
        $tail = @()
        foreach ($f in @($backendErr, $backendOut)) {
            if (Test-Path $f) { $tail += @(Get-Content $f -Tail 30) }
        }
        Fail 'Backend did not answer within 60 seconds.' ($tail + @(
            'Most common fixes:'
            '  1. Another program is using port 8000  ->  run .\stop.ps1, then .\start.ps1'
            '  2. See the exact error by running manually:'
            "       cd `"$backendDir`""
            "       python -m uvicorn app.main:app --port 8000"
        ))
    }
    $movies = '...'
    if ($health.Body) {
        try { $movies = (ConvertFrom-Json $health.Body).master_movies } catch {}
    }
    Write-Host "  [1/2] Backend  OK   http://127.0.0.1:8000  ($movies movies loaded)" -ForegroundColor Green
}

# ---- start frontend -----------------------------------------------------
if ($startF) {
    Write-Host -NoNewline '  [2/2] Starting frontend'
    try {
        $frontendProc = Start-Process -FilePath 'npm.cmd' `
            -ArgumentList 'run', 'dev' `
            -WorkingDirectory $frontendDir `
            -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr `
            -PassThru
    } catch {
        Stop-Tree $backendProc
        Fail 'Could not start the frontend (is npm/Node.js installed?)' @("$($_.Exception.Message)", "Folder: $frontendDir", "$($_.ScriptStackTrace)")
    }

    $fe = Wait-Endpoint 'http://localhost:5173/' 30
    Write-Host ''
    if (-not $fe.Up) {
        Stop-Tree $backendProc
        Stop-Tree $frontendProc
        $tail = @()
        foreach ($f in @($frontendErr, $frontendOut)) {
            if (Test-Path $f) { $tail += @(Get-Content $f -Tail 30) }
        }
        Fail 'Frontend did not answer within 30 seconds.' ($tail + @(
            'Most common fix: run .\stop.ps1, then .\start.ps1 again.'
        ))
    }
    Write-Host '  [2/2] Frontend OK   http://localhost:5173' -ForegroundColor Green
}

# ---- live log tail ------------------------------------------------------
$logs = @()
if ($startB) {
    $logs += @{ Path = $backendErr;  Name = 'backend';  Seen = 0 }
    $logs += @{ Path = $backendOut;  Name = 'backend';  Seen = 0 }
}
if ($startF) {
    $logs += @{ Path = $frontendErr; Name = 'frontend'; Seen = 0 }
    $logs += @{ Path = $frontendOut; Name = 'frontend'; Seen = 0 }
}
foreach ($log in $logs) { Show-New $log }

Write-Host ''
Write-Host '  ------------------------------------------------------------' -ForegroundColor Yellow
if ($startB -and $startF) {
    Write-Host '  CineMine is running' -ForegroundColor Green
    Write-Host '  OPEN     http://localhost:5173' -ForegroundColor Cyan
    Write-Host '  LOGIN    demo@cinemine.dev  /  secret123'
    Write-Host '  (or register a new account)'
    Write-Host '  STOP     press ENTER in this window'
} elseif ($startB) {
    Write-Host '  Backend running - http://127.0.0.1:8000/docs' -ForegroundColor Green
    Write-Host '  STOP     press ENTER in this window'
} else {
    Write-Host '  Frontend running - http://localhost:5173' -ForegroundColor Green
    Write-Host '  (backend must also be running: .\start.ps1)' -ForegroundColor DarkYellow
    Write-Host '  STOP     press ENTER in this window'
}
Write-Host '  ------------------------------------------------------------' -ForegroundColor Yellow
Write-Host '  Server messages appear below as [backend] / [frontend] lines.'
Write-Host ''

# ---- monitor until ENTER or a server dies -------------------------------
$crashed = $null
while ($true) {
    foreach ($log in $logs) { Show-New $log }

    if ($startB -and $backendProc.HasExited)  { $crashed = 'backend';  break }
    if ($startF -and $frontendProc.HasExited) { $crashed = 'frontend'; break }

    try {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            if ($key.Key -eq 'Enter') { break }
        }
    } catch { }

    Start-Sleep -Milliseconds 800
}

# ---- stop ---------------------------------------------------------------
if ($crashed -and (Test-Path $marker)) {
    Remove-Item $marker -ErrorAction SilentlyContinue
    Stop-Tree $backendProc
    Stop-Tree $frontendProc
    Write-Host ''
    Write-Host '  [OK] Stopped by .\stop.ps1 - ports are free.' -ForegroundColor Green
    Write-Host ''
    exit 0
}

Stop-Tree $backendProc
Stop-Tree $frontendProc

if ($crashed) {
    $tail = @()
    foreach ($f in @($backendErr, $backendOut, $frontendErr, $frontendOut)) {
        if (Test-Path $f) { $tail += @(Get-Content $f -Tail 30) }
    }
    Fail "The $crashed server stopped unexpectedly." ($tail + @(
        'What to do next:'
        '  1. Run .\stop.ps1 to clean everything up'
        '  2. Read the server messages above - they contain the real error'
        '  3. Run .\start.ps1 again'
    ))
}

foreach ($p in 8000, 5173) {
    for ($i = 0; $i -lt 5; $i++) {
        if (-not (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)) { break }
        Start-Sleep -Milliseconds 400
    }
}
Remove-Item $marker -ErrorAction SilentlyContinue

Write-Host ''
Write-Host '  [OK] Both servers stopped - ports 5173 and 8000 are free.' -ForegroundColor Green
Write-Host '  Start again anytime with:  .\start.ps1'
Write-Host ''
exit 0

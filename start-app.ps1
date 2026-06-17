$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dashboard = Join-Path $root "dashboard"
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Python virtual environment was not found. Run: python -m venv .venv"
}

if (-not (Test-Path (Join-Path $dashboard "node_modules"))) {
    Write-Error "Dashboard dependencies were not found. Run: cd dashboard; npm.cmd install"
}

Write-Host "Starting Bookkeeping App..."
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Press Ctrl+C to stop both servers."
Write-Host ""

$backend = Start-Job -Name "bookkeeping-backend" -ScriptBlock {
    param($rootPath, $pythonPath)
    Set-Location $rootPath
    & $pythonPath -m uvicorn bookkeeping_app.main:app --host 127.0.0.1 --port 8000 2>&1 |
        ForEach-Object { $_.ToString() }
} -ArgumentList $root, $python

$frontend = Start-Job -Name "bookkeeping-frontend" -ScriptBlock {
    param($dashboardPath)
    Set-Location $dashboardPath
    & npm.cmd run dev 2>&1 |
        ForEach-Object { $_.ToString() }
} -ArgumentList $dashboard

try {
    while ($true) {
        foreach ($job in @($backend, $frontend)) {
            Receive-Job -Job $job -ErrorAction Continue
            if ($job.State -notin @("Running", "NotStarted")) {
                throw "$($job.Name) stopped with state $($job.State)."
            }
        }
        Start-Sleep -Milliseconds 500
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping Bookkeeping App..."
    Stop-Job -Job $backend, $frontend -ErrorAction SilentlyContinue
    Remove-Job -Job $backend, $frontend -Force -ErrorAction SilentlyContinue
}

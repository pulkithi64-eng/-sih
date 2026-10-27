$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$statePath = Join-Path $repoRoot '.local-run\server.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Output 'No local server state found.'; exit 0 }
$serverState = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$expectedPython = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'))
$serverProcess = Get-Process -Id $serverState.pid -ErrorAction SilentlyContinue
if (-not $serverProcess) { Write-Output 'The local server is already stopped.'; exit 0 }
if ($serverProcess.Path -ne $expectedPython) { throw 'Saved process ID belongs to another executable; refusing to stop it.' }
& (Join-Path $env:SystemRoot 'System32\taskkill.exe') /PID $serverProcess.Id /T /F | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not stop the local server process tree.' }
Write-Output 'VeriSense stopped. Database and uploaded files are preserved.'

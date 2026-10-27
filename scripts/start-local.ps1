param([int]$Port = 8001)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$runtimePath = Join-Path $repoRoot '.local-run'
$pythonPath = Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'
$frontendPath = Join-Path $repoRoot 'frontend\dist'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Backend dependencies are missing. Install them with uv sync --frozen in backend.' }
if (-not (Test-Path -LiteralPath (Join-Path $frontendPath 'index.html'))) { throw 'Frontend build is missing. Run npm ci and npm run build in frontend.' }
New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null
try {
    $existing = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health/live" -TimeoutSec 2
    if ($existing.status -eq 'alive') { Write-Output "VeriSense is already running at http://127.0.0.1:$Port"; exit 0 }
} catch { }
$secretPath = Join-Path $runtimePath '.jwt-secret'
if (-not (Test-Path -LiteralPath $secretPath)) {
    $randomBytes = New-Object byte[] 48
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($randomBytes) } finally { $generator.Dispose() }
    [System.IO.File]::WriteAllText($secretPath, [Convert]::ToBase64String($randomBytes))
}
$env:VERISENSE_SECRET = [System.IO.File]::ReadAllText($secretPath).Trim()
$env:VERISENSE_ENVIRONMENT = 'local'
$env:VERISENSE_DEMO_MODE = 'true'
$env:VERISENSE_FRONTEND_DIR = $frontendPath
$env:VERISENSE_MOCK_MODE = 'inprocess'
$env:VERISENSE_AUTOSEED = 'true'
$env:VERISENSE_OCR_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$serverProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$Port") -WorkingDirectory (Join-Path $repoRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimePath 'server.out.log') -RedirectStandardError (Join-Path $runtimePath 'server.err.log') -PassThru
@{ pid = $serverProcess.Id; port = $Port; url = "http://127.0.0.1:$Port"; startedAt = [DateTimeOffset]::Now.ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimePath 'server.json') -Encoding UTF8
Write-Output "Started VeriSense process $($serverProcess.Id). URL: http://127.0.0.1:$Port"
Write-Output 'First startup seeds synthetic documents and may take several minutes. Logs: .local-run/server.err.log'

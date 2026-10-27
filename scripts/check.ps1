param([string]$Report = "docs/check-results.json")
$ErrorActionPreference = 'Continue'
$repoRoot = Split-Path -Parent $PSScriptRoot
$results = @()
$checks = @(
    @{ Dir = 'frontend'; Tool = 'npm'; Args = @('run', 'lint') },
    @{ Dir = 'frontend'; Tool = 'npm'; Args = @('run', 'typecheck') },
    @{ Dir = 'frontend'; Tool = 'npm'; Args = @('test') },
    @{ Dir = 'frontend'; Tool = 'npm'; Args = @('run', 'build') },
    @{ Dir = 'backend'; Tool = 'uv'; Args = @('run', '--frozen', 'pytest') },
    @{ Dir = 'frontend'; Tool = 'npm'; Args = @('audit', '--omit=dev', '--audit-level=high') },
    @{ Dir = '.'; Tool = 'docker'; Args = @('compose', 'config', '--quiet') }
)
foreach ($check in $checks) {
    $label = "$($check.Tool) $($check.Args -join ' ')"
    if (-not (Get-Command $check.Tool -ErrorAction SilentlyContinue)) {
        $results += [pscustomobject]@{ directory = $check.Dir; command = $label; status = 'NOT RUN'; reason = "$($check.Tool) is not installed or on PATH" }
        continue
    }
    Push-Location (Join-Path $repoRoot $check.Dir)
    try {
        $toolName = $check.Tool
        $toolArgs = $check.Args
        & $toolName @toolArgs
        $results += [pscustomobject]@{ directory = $check.Dir; command = $label; status = $(if ($LASTEXITCODE -eq 0) { 'PASS' } else { 'FAIL' }); reason = "exit code $LASTEXITCODE" }
    } finally { Pop-Location }
}
$results | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $repoRoot $Report) -Encoding UTF8
$results | Format-Table -AutoSize
if (@($results | Where-Object { $_.status -ne 'PASS' }).Count) { exit 1 }

# Start the VeriSense backend on http://localhost:8001 (frontend dev server proxies /api and /mock here).
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
uv sync
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run uvicorn app.main:app --port 8001 --reload

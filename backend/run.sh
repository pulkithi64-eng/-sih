#!/usr/bin/env bash
# Start the VeriSense backend on http://localhost:8001 (frontend dev server proxies /api and /mock here).
set -euo pipefail
cd "$(dirname "$0")"
uv sync
exec uv run uvicorn app.main:app --port 8001 --reload

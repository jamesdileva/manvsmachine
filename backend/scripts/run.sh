#!/usr/bin/env bash
# Run the backend (release mode: serves the built frontend on the same port).
#
#   bash backend/scripts/run.sh
#
# Single port: http://127.0.0.1:8000 serves the API, the WebSocket, and the
# built UI (frontend/dist). Build first:  bash frontend/scripts/build.sh
#
# No Docker required.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT/backend"
exec "${PYTHON:-python}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

#!/usr/bin/env bash
# Build the frontend for the single-port release (Sprint 27).
#
#   bash frontend/scripts/build.sh
#
# VITE_API_BASE_URL comes from frontend/.env.production: the built UI talks to
# the FastAPI app on its own origin, so the release runs on one port.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  echo "frontend deps missing - run 'npm install' in frontend/ first" >&2
  exit 1
fi
npm run build
echo "built frontend/dist - serve it with: bash backend/scripts/run.sh"

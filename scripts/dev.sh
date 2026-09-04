#!/usr/bin/env bash
# Start SiteProbe: FastAPI backend (:8000) + Vite dev dashboard (:5173).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Prefer Node 20 from nvm if present (system Node may be too old for Vite).
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
  nvm use 20.2.0 >/dev/null 2>&1 || true
fi

echo "==> Starting API on http://127.0.0.1:8000 (docs at /docs)"
cd "$ROOT/server"
if [ ! -x .venv/bin/python ]; then
  echo "Server venv missing - run setup first (see README.md)"
  exit 1
fi
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

echo "==> Starting dashboard on http://localhost:4500"
cd "$ROOT/client"
[ -d node_modules ] || npm install --no-audit --no-fund
npm run dev &
WEB_PID=$!

trap 'kill $API_PID $WEB_PID 2>/dev/null' EXIT
echo "==> SiteProbe is running: dashboard http://localhost:4500 · API http://127.0.0.1:8000/docs"
wait

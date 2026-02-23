#!/usr/bin/env bash
# ============================================================
#  UTAP Demo Launcher
#  Starts a self-contained SQLite demo (no Postgres / AWS / SAML needed)
# ============================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
PORT="${PORT:-8080}"

echo ""
echo "======================================================"
echo "  UTAP — Unit Test Artefact Portal (Demo Mode)"
echo "======================================================"

# 1. Check Python
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 is required. Install it and re-run."
  exit 1
fi

# 2. Install Python deps (skip if venv already exists)
if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo ""
  echo "▶  Creating Python virtual environment..."
  python3 -m venv "$BACKEND_DIR/.venv"
fi
source "$BACKEND_DIR/.venv/bin/activate" 2>/dev/null || true

echo "▶  Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet \
  fastapi uvicorn[standard] sqlalchemy structlog \
  python-multipart starlette reportlab 2>&1 | grep -v "^Requirement already"

# 3. Build frontend if dist is missing (requires Node.js + npm)
if [ ! -f "$FRONTEND_DIR/dist/index.html" ]; then
  echo ""
  echo "▶  Frontend dist not found — building with npm..."
  if ! command -v npm &>/dev/null; then
    echo "ERROR: npm is required to build the frontend."
    echo "       Install Node.js ≥ 18 or copy a pre-built frontend/dist/ directory."
    exit 1
  fi
  cd "$FRONTEND_DIR"
  npm install --silent
  npm run build -- --config vite.config.demo.ts 2>&1 | tail -5
  cd "$SCRIPT_DIR"
fi

# 4. Launch demo server
echo ""
echo "▶  Starting UTAP Demo on http://localhost:${PORT}"
echo "   Demo login options:"
echo "     • Admin         →  admin@utap.demo"
echo "     • Developer     →  developer@utap.demo"
echo "     • Reviewer      →  reviewer@utap.demo"
echo "     • Release Mgr   →  release@utap.demo"
echo ""
echo "   Press Ctrl+C to stop."
echo "======================================================"
echo ""

cd "$BACKEND_DIR"
PORT=$PORT python3 demo_server.py

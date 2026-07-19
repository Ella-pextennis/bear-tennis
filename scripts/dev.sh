#!/usr/bin/env bash
# Start backend (FastAPI) and frontend (Vite) together. Ctrl+C stops both.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

BACKEND_PID=""
FRONTEND_PID=""

# Make locally-installed Node discoverable (e.g. $HOME/.local/node/bin)
if ! command -v node >/dev/null 2>&1 && [ -x "$HOME/.local/node/bin/node" ]; then
  export PATH="$HOME/.local/node/bin:$PATH"
fi

cleanup() {
  echo ""
  echo ">> 正在停止服务..."
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  # uvicorn --reload spawns a reloader child; clean it up too
  pkill -P "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# --- Backend ---------------------------------------------------------------
echo ">> 启动后端 (FastAPI @ http://localhost:8000, docs @ /docs) ..."
(
  cd "$PROJECT_ROOT/backend"
  if [ ! -d .venv ]; then
    python3 -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install --quiet --upgrade pip
  pip install --quiet -e .
  exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) &
BACKEND_PID=$!

# --- Frontend --------------------------------------------------------------
echo ">> 启动前端 (Vite @ http://localhost:5173) ..."
(
  cd "$PROJECT_ROOT/frontend"
  if [ ! -d node_modules ]; then
    echo "   首次运行，安装依赖（可能耗时 1-2 分钟）..."
    npm install
  fi
  exec npm run dev
) &
FRONTEND_PID=$!

echo ""
echo "========================================"
echo " 服务已启动"
echo "   前端: http://localhost:5173"
echo "   后端: http://localhost:8000/docs"
echo "   Ctrl+C 退出"
echo "========================================"

wait

#!/usr/bin/env bash
# FolderDiff GUI 실행 스크립트
# 사용법: ./run-gui.sh [--port 8000]

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
GUI="$ROOT/gui"
PORT="${1:-8000}"

# ── 의존성 확인 및 설치 ────────────────────────────────────────────────────
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "→ 의존성 설치 중…"
  pip3 install -r "$GUI/backend/requirements.txt" --break-system-packages -q
fi

# ── 서버 시작 ──────────────────────────────────────────────────────────────
echo "→ 서버 시작: http://localhost:$PORT"

# 브라우저 자동 오픈 (백그라운드에서 잠시 후 실행)
(sleep 1 && open "http://localhost:$PORT") &

cd "$ROOT"
python3 -m uvicorn gui.backend.main:app --host 0.0.0.0 --port "$PORT" --reload

#!/usr/bin/env bash
# FolderDiff TUI 실행 스크립트
# 사용법: ./run-tui.sh <왼쪽_경로> <오른쪽_경로>

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TUI="$ROOT/tui"

# ── 의존성 확인 및 설치 ────────────────────────────────────────────────────
if ! python3 -c "import textual" 2>/dev/null; then
  echo "→ 의존성 설치 중…"
  pip3 install -r "$TUI/requirements.txt" --break-system-packages -q
fi

# ── 실행 ──────────────────────────────────────────────────────────────────
cd "$TUI"
python3 main.py "$@"

#!/usr/bin/env bash
# FolderDiff 테스트 실행 스크립트
# 사용법:
#   ./run-tests.sh          전체 테스트
#   ./run-tests.sh tui      TUI 테스트만
#   ./run-tests.sh gui      GUI 백엔드 테스트만

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-all}"

run_tui() {
  echo "══ TUI 테스트 ════════════════════════════════"
  cd "$ROOT/tui"
  python3 -m pytest tests/ -v
}

run_gui() {
  echo "══ GUI 백엔드 테스트 ═════════════════════════"
  cd "$ROOT"
  python3 -m pytest gui/backend/tests/ -v
}

case "$TARGET" in
  tui) run_tui ;;
  gui) run_gui ;;
  all)
    run_tui
    echo
    run_gui
    ;;
  *)
    echo "사용법: $0 [tui|gui|all]"
    exit 1
    ;;
esac

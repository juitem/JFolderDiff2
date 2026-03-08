#!/usr/bin/env python3
"""FolderDiff — 폴더/파일 비교 및 머지 도구.

사용법:
    python main.py <왼쪽_경로> <오른쪽_경로>

키보드 단축키:
    [폴더 화면]
      ↑↓ / j k   항목 이동
      Enter       파일 열기 / 폴더 펼치기
      Space       폴더 펼치기/접기
      Tab         다음 diff 항목으로 이동
      f           diff 항목만 필터링 (토글)
      r           새로고침
      q           종료

    [파일 diff 화면]
      ↑↓ / j k   스크롤
      PgUp/PgDn  페이지 스크롤
      n / Tab     다음 diff 청크
      p / S-Tab   이전 diff 청크
      →  / l      현재 청크 왼쪽 채택 (오른쪽 파일에 반영)
      ←  / h      현재 청크 오른쪽 채택 (왼쪽 파일에 반영)
      Ctrl+→      모든 청크 왼쪽 채택
      Ctrl+←      모든 청크 오른쪽 채택
      u           현재 청크 결정 취소
      s / Ctrl+S  저장
      b / Esc     폴더 화면으로 돌아가기
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FolderDiff — 폴더/파일 비교 및 머지 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("left", help="왼쪽 폴더 경로")
    parser.add_argument("right", help="오른쪽 폴더 경로")
    parser.add_argument(
        "--config", "-c",
        metavar="경로",
        help=(
            "제외 설정 파일 경로 (.folderdiff.toml). "
            "미지정 시 왼쪽 폴더 → 오른쪽 폴더 → 현재 디렉터리 → 홈 디렉터리 순으로 탐색."
        ),
    )
    args = parser.parse_args()

    left_path = Path(args.left).expanduser().resolve()
    right_path = Path(args.right).expanduser().resolve()

    errors = []
    if not left_path.exists():
        errors.append(f"왼쪽 경로가 존재하지 않습니다: {left_path}")
    if not right_path.exists():
        errors.append(f"오른쪽 경로가 존재하지 않습니다: {right_path}")
    if errors:
        for e in errors:
            print(f"오류: {e}")
        sys.exit(1)

    from src.config import load_config
    from src.app import FolderDiffApp

    try:
        config_path = Path(args.config) if args.config else None
        exclude_config = load_config(
            explicit=config_path,
            left=left_path,
            right=right_path,
        )
    except FileNotFoundError as e:
        print(f"오류: {e}")
        sys.exit(1)

    app = FolderDiffApp(left_path, right_path, exclude_config)
    app.run()


if __name__ == "__main__":
    main()

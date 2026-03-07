"""파일 I/O 유틸리티."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

_BINARY_CHECK_SIZE = 1024
_ENCODINGS = ("utf-8", "latin-1", "cp1252")


def is_binary(path: Path) -> bool:
    """파일이 바이너리인지 확인한다."""
    try:
        with open(path, "rb") as f:
            return b"\x00" in f.read(_BINARY_CHECK_SIZE)
    except OSError:
        return True


def read_lines(path: Optional[Path]) -> Tuple[List[str], Optional[str]]:
    """파일 줄을 읽는다. (lines, error_message) 튜플을 반환한다.

    바이너리 파일이거나 읽을 수 없으면 빈 목록과 오류 메시지를 반환한다.
    """
    if path is None:
        return [], "경로가 None입니다"
    if not path.exists():
        return [], "파일이 존재하지 않습니다"
    if is_binary(path):
        return [], "바이너리 파일"

    for enc in _ENCODINGS:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.readlines(), None
        except (UnicodeDecodeError, OSError):
            continue

    return [], "파일 인코딩을 인식할 수 없습니다"


def write_lines(path: Path, lines: List[str]) -> Optional[str]:
    """줄 목록을 파일에 쓴다. 실패 시 오류 메시지를 반환한다."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return None
    except OSError as e:
        return str(e)

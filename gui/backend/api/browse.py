"""파일시스템 탐색 API."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/browse", tags=["browse"])


class FsEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: Optional[int]
    modified: Optional[str]


class BrowseResponse(BaseModel):
    path: str
    parent: Optional[str]
    entries: List[FsEntry]


@router.get("", response_model=BrowseResponse)
def browse(path: str = Query(..., description="탐색할 절대 경로")) -> BrowseResponse:
    """특정 경로 안의 파일·폴더 목록을 반환한다."""
    resolved = _safe_resolve(path)

    if not resolved.exists():
        raise HTTPException(status_code=400, detail=f"경로가 존재하지 않습니다: {path}")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"디렉터리가 아닙니다: {path}")

    try:
        raw = list(resolved.iterdir())
    except PermissionError:
        raise HTTPException(status_code=403, detail="접근 권한이 없습니다")

    # 폴더 먼저, 그 다음 파일 — 각 그룹 내부는 이름 오름차순
    dirs = sorted([p for p in raw if p.is_dir()], key=lambda p: p.name.lower())
    files = sorted([p for p in raw if p.is_file()], key=lambda p: p.name.lower())

    entries: List[FsEntry] = []
    for p in dirs + files:
        try:
            stat = p.stat()
            size = stat.st_size if p.is_file() else None
            modified = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
        except OSError:
            size = None
            modified = None

        entries.append(
            FsEntry(
                name=p.name,
                path=str(p),
                is_dir=p.is_dir(),
                size=size,
                modified=modified,
            )
        )

    parent = str(resolved.parent) if resolved != resolved.parent else None

    return BrowseResponse(path=str(resolved), parent=parent, entries=entries)


def _safe_resolve(path: str) -> Path:
    """경로를 절대 경로로 변환한다. 홈 디렉터리 확장 지원."""
    return Path(path).expanduser().resolve()

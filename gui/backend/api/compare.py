"""폴더/파일 비교 API."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..config import load_config
from ..models.diff_engine import (
    AlignedLine,
    DiffChunk,
    build_aligned_lines,
    compute_diff,
    get_change_chunks,
)
from ..models.folder_diff import FolderEntry as ModelEntry, compare_folders, flatten_entries
from ..utils.file_utils import read_lines

router = APIRouter(prefix="/api", tags=["compare"])


# ── 폴더 비교 모델 ────────────────────────────────────────────────────────────


class FolderEntryDTO(BaseModel):
    name: str
    rel_path: str
    is_dir: bool
    status: str
    left_abs: Optional[str]
    right_abs: Optional[str]
    depth: int
    children: List["FolderEntryDTO"] = []


class CompareStats(BaseModel):
    same: int
    different: int
    left_only: int
    right_only: int
    total: int


class CompareFolderResponse(BaseModel):
    left: str
    right: str
    stats: CompareStats
    entries: List[FolderEntryDTO]


# ── 파일 diff 모델 ────────────────────────────────────────────────────────────


class ChunkDTO(BaseModel):
    index: int
    tag: str
    left_start: int
    left_end: int
    right_start: int
    right_end: int


class AlignedLineDTO(BaseModel):
    left_lineno: Optional[int]
    right_lineno: Optional[int]
    left_text: str
    right_text: str
    chunk_idx: int
    tag: str


class DiffFileResponse(BaseModel):
    left_path: Optional[str]
    right_path: Optional[str]
    error: Optional[str]
    change_count: int
    chunks: List[ChunkDTO]
    aligned: List[AlignedLineDTO]


# ── 엔드포인트 ────────────────────────────────────────────────────────────────


@router.get("/compare", response_model=CompareFolderResponse)
def compare_folder(
    left: str = Query(..., description="왼쪽 폴더 절대 경로"),
    right: str = Query(..., description="오른쪽 폴더 절대 경로"),
    config: Optional[str] = Query(None, description="제외 설정 파일 절대 경로 (.folderdiff.toml)"),
) -> CompareFolderResponse:
    """두 폴더를 재귀적으로 비교한다."""
    from pathlib import Path as _Path
    l_path = _resolve_dir(left, "left")
    r_path = _resolve_dir(right, "right")

    try:
        exclude = load_config(
            explicit=_Path(config) if config else None,
            left=l_path,
            right=r_path,
        )
    except FileNotFoundError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))

    entries = compare_folders(l_path, r_path, exclude)
    flat = flatten_entries(entries, expanded=None)

    same = sum(1 for e in flat if e.status == "same" and not e.is_dir)
    different = sum(1 for e in flat if e.status == "different" and not e.is_dir)
    left_only = sum(1 for e in flat if e.status == "left_only")
    right_only = sum(1 for e in flat if e.status == "right_only")
    total = len([e for e in flat if not e.is_dir])

    return CompareFolderResponse(
        left=str(l_path),
        right=str(r_path),
        stats=CompareStats(
            same=same,
            different=different,
            left_only=left_only,
            right_only=right_only,
            total=total,
        ),
        entries=[_to_dto(e) for e in entries],
    )


@router.get("/diff", response_model=DiffFileResponse)
def diff_file(
    left: Optional[str] = Query(None, description="왼쪽 파일 절대 경로"),
    right: Optional[str] = Query(None, description="오른쪽 파일 절대 경로"),
) -> DiffFileResponse:
    """두 파일을 줄 단위로 비교한다."""
    l_path = Path(left).expanduser().resolve() if left else None
    r_path = Path(right).expanduser().resolve() if right else None

    left_lines, l_err = read_lines(l_path)
    right_lines, r_err = read_lines(r_path)

    error = l_err or r_err
    if error:
        return DiffFileResponse(
            left_path=str(l_path) if l_path else None,
            right_path=str(r_path) if r_path else None,
            error=error,
            change_count=0,
            chunks=[],
            aligned=[],
        )

    chunks = compute_diff(left_lines, right_lines)
    aligned = build_aligned_lines(chunks)
    change_count = len(get_change_chunks(chunks))

    return DiffFileResponse(
        left_path=str(l_path) if l_path else None,
        right_path=str(r_path) if r_path else None,
        error=None,
        change_count=change_count,
        chunks=[
            ChunkDTO(
                index=i,
                tag=c.tag,
                left_start=c.left_start,
                left_end=c.left_end,
                right_start=c.right_start,
                right_end=c.right_end,
            )
            for i, c in enumerate(chunks)
        ],
        aligned=[
            AlignedLineDTO(
                left_lineno=a.left_lineno,
                right_lineno=a.right_lineno,
                left_text=a.left_text,
                right_text=a.right_text,
                chunk_idx=a.chunk_idx,
                tag=a.tag,
            )
            for a in aligned
        ],
    )


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────


def _resolve_dir(raw: str, label: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"{label} 경로가 존재하지 않습니다: {raw}")
    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"{label} 경로가 폴더가 아닙니다: {raw}")
    return path


def _to_dto(e: ModelEntry) -> FolderEntryDTO:
    return FolderEntryDTO(
        name=e.name,
        rel_path=e.rel_path,
        is_dir=e.is_dir,
        status=e.status,
        left_abs=str(e.left_abs) if e.left_abs else None,
        right_abs=str(e.right_abs) if e.right_abs else None,
        depth=e.depth,
        children=[_to_dto(c) for c in e.children],
    )

"""머지 결정 적용 및 저장 API."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models.diff_engine import compute_diff, get_change_chunks
from ..models.merge_state import MergeDecision, MergeState
from ..utils.file_utils import read_lines, write_lines

router = APIRouter(prefix="/api/merge", tags=["merge"])


class MergeRequest(BaseModel):
    left_path: Optional[str] = None
    right_path: Optional[str] = None
    decisions: Dict[str, str]  # {chunk_idx(str): "left" | "right"}


class MergeResponse(BaseModel):
    success: bool
    saved_files: List[str]
    message: str


@router.post("", response_model=MergeResponse)
def merge_file(body: MergeRequest) -> MergeResponse:
    """머지 결정을 적용하여 파일을 저장한다."""
    l_path = _resolve_file_opt(body.left_path, "left")
    r_path = _resolve_file_opt(body.right_path, "right")

    if not body.decisions:
        return MergeResponse(success=False, saved_files=[], message="저장할 결정이 없습니다")

    left_lines, l_err = read_lines(l_path)
    right_lines, r_err = read_lines(r_path)

    if l_err and l_path:
        raise HTTPException(status_code=400, detail=f"왼쪽 파일 읽기 실패: {l_err}")
    if r_err and r_path:
        raise HTTPException(status_code=400, detail=f"오른쪽 파일 읽기 실패: {r_err}")

    chunks = compute_diff(left_lines, right_lines)
    state = MergeState(len(chunks))

    # 문자열 키 → int 변환, 결정 적용
    for str_idx, decision_str in body.decisions.items():
        try:
            idx = int(str_idx)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"유효하지 않은 청크 인덱스: {str_idx}")

        if idx < 0 or idx >= len(chunks):
            raise HTTPException(status_code=400, detail=f"청크 인덱스 범위 초과: {idx}")

        try:
            decision = MergeDecision[decision_str.upper()]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"유효하지 않은 결정값: {decision_str}")

        state.set(idx, decision)

    saved_files: List[str] = []
    errors: List[str] = []

    # LEFT 결정이 있으면 오른쪽 파일 저장
    if state.is_right_modified() and r_path:
        new_right = state.apply_to_right(chunks)
        err = write_lines(r_path, new_right)
        if err:
            errors.append(f"오른쪽 파일 저장 실패: {err}")
        else:
            saved_files.append(str(r_path))

    # RIGHT 결정이 있으면 왼쪽 파일 저장
    if state.is_left_modified() and l_path:
        new_left = state.apply_to_left(chunks)
        err = write_lines(l_path, new_left)
        if err:
            errors.append(f"왼쪽 파일 저장 실패: {err}")
        else:
            saved_files.append(str(l_path))

    if errors:
        raise HTTPException(status_code=500, detail="\n".join(errors))

    return MergeResponse(
        success=True,
        saved_files=saved_files,
        message=f"저장 완료: {', '.join(saved_files)}",
    )


def _resolve_file_opt(raw: Optional[str], label: str) -> Optional[Path]:
    if raw is None:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"{label} 파일이 존재하지 않습니다: {raw}")
    return path

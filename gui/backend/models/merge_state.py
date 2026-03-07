"""머지 결정 상태 관리."""
from __future__ import annotations

from enum import Enum
from typing import Dict, List

from .diff_engine import DiffChunk


class MergeDecision(Enum):
    NONE = "none"
    LEFT = "left"    # 이 청크에서 왼쪽 내용을 채택
    RIGHT = "right"  # 이 청크에서 오른쪽 내용을 채택


class MergeState:
    """각 diff 청크에 대한 머지 결정을 추적한다."""

    def __init__(self, num_chunks: int) -> None:
        self.num_chunks = num_chunks
        self.decisions: Dict[int, MergeDecision] = {}

    # ------------------------------------------------------------------ queries

    def get(self, chunk_idx: int) -> MergeDecision:
        return self.decisions.get(chunk_idx, MergeDecision.NONE)

    def is_left_modified(self) -> bool:
        """RIGHT 결정이 있으면 왼쪽 파일이 수정된다."""
        return any(d == MergeDecision.RIGHT for d in self.decisions.values())

    def is_right_modified(self) -> bool:
        """LEFT 결정이 있으면 오른쪽 파일이 수정된다."""
        return any(d == MergeDecision.LEFT for d in self.decisions.values())

    def has_any_decision(self) -> bool:
        return bool(self.decisions)

    # ----------------------------------------------------------------- mutations

    def set(self, chunk_idx: int, decision: MergeDecision) -> None:
        if decision == MergeDecision.NONE:
            self.decisions.pop(chunk_idx, None)
        else:
            self.decisions[chunk_idx] = decision

    def accept_all_left(self, change_indices: List[int]) -> None:
        """모든 변경 청크에서 왼쪽을 채택한다."""
        for idx in change_indices:
            self.decisions[idx] = MergeDecision.LEFT

    def accept_all_right(self, change_indices: List[int]) -> None:
        """모든 변경 청크에서 오른쪽을 채택한다."""
        for idx in change_indices:
            self.decisions[idx] = MergeDecision.RIGHT

    def clear(self) -> None:
        self.decisions.clear()

    # ------------------------------------------------------------------ apply

    def apply_to_right(self, chunks: List[DiffChunk]) -> List[str]:
        """결정을 적용하여 새 오른쪽 파일 내용을 생성한다.

        LEFT 결정 청크는 왼쪽 내용으로 덮어쓴다.
        결정 없는 청크는 기존 오른쪽 내용을 유지한다.
        """
        result: List[str] = []
        for i, chunk in enumerate(chunks):
            decision = self.get(i)
            if chunk.tag == "equal":
                result.extend(chunk.right_lines)
            elif decision == MergeDecision.LEFT:
                result.extend(chunk.left_lines)
            else:
                result.extend(chunk.right_lines)
        return result

    def apply_to_left(self, chunks: List[DiffChunk]) -> List[str]:
        """결정을 적용하여 새 왼쪽 파일 내용을 생성한다.

        RIGHT 결정 청크는 오른쪽 내용으로 덮어쓴다.
        결정 없는 청크는 기존 왼쪽 내용을 유지한다.
        """
        result: List[str] = []
        for i, chunk in enumerate(chunks):
            decision = self.get(i)
            if chunk.tag == "equal":
                result.extend(chunk.left_lines)
            elif decision == MergeDecision.RIGHT:
                result.extend(chunk.right_lines)
            else:
                result.extend(chunk.left_lines)
        return result

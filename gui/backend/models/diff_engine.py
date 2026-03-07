"""줄 단위 diff 계산 엔진 (difflib 기반)."""
from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DiffChunk:
    """단일 diff 연산 블록."""

    tag: str          # 'equal' | 'replace' | 'insert' | 'delete'
    left_start: int   # left_lines 내 0-based 시작 인덱스
    left_end: int
    right_start: int  # right_lines 내 0-based 시작 인덱스
    right_end: int
    left_lines: List[str]
    right_lines: List[str]

    @property
    def is_change(self) -> bool:
        return self.tag != "equal"


@dataclass
class AlignedLine:
    """사이드-바이-사이드 diff 뷰의 한 행."""

    left_lineno: Optional[int]   # 1-based; 해당 없으면 None
    right_lineno: Optional[int]  # 1-based; 해당 없으면 None
    left_text: str
    right_text: str
    chunk_idx: int
    tag: str  # 'equal' | 'replace' | 'insert' | 'delete'


def compute_diff(left_lines: List[str], right_lines: List[str]) -> List[DiffChunk]:
    """두 줄 목록 사이의 diff 청크를 계산한다."""
    matcher = difflib.SequenceMatcher(None, left_lines, right_lines, autojunk=False)
    chunks: List[DiffChunk] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        chunks.append(
            DiffChunk(
                tag=tag,
                left_start=i1,
                left_end=i2,
                right_start=j1,
                right_end=j2,
                left_lines=left_lines[i1:i2],
                right_lines=right_lines[j1:j2],
            )
        )
    return chunks


def build_aligned_lines(chunks: List[DiffChunk]) -> List[AlignedLine]:
    """사이드-바이-사이드 표시를 위해 정렬된 행 목록을 생성한다."""
    aligned: List[AlignedLine] = []

    for chunk_idx, chunk in enumerate(chunks):
        if chunk.tag == "equal":
            for i in range(len(chunk.left_lines)):
                aligned.append(
                    AlignedLine(
                        left_lineno=chunk.left_start + i + 1,
                        right_lineno=chunk.right_start + i + 1,
                        left_text=chunk.left_lines[i].rstrip("\n"),
                        right_text=chunk.right_lines[i].rstrip("\n"),
                        chunk_idx=chunk_idx,
                        tag="equal",
                    )
                )

        elif chunk.tag == "replace":
            n = max(len(chunk.left_lines), len(chunk.right_lines))
            for i in range(n):
                has_left = i < len(chunk.left_lines)
                has_right = i < len(chunk.right_lines)
                aligned.append(
                    AlignedLine(
                        left_lineno=chunk.left_start + i + 1 if has_left else None,
                        right_lineno=chunk.right_start + i + 1 if has_right else None,
                        left_text=chunk.left_lines[i].rstrip("\n") if has_left else "",
                        right_text=chunk.right_lines[i].rstrip("\n") if has_right else "",
                        chunk_idx=chunk_idx,
                        tag="replace",
                    )
                )

        elif chunk.tag == "delete":
            for i, line in enumerate(chunk.left_lines):
                aligned.append(
                    AlignedLine(
                        left_lineno=chunk.left_start + i + 1,
                        right_lineno=None,
                        left_text=line.rstrip("\n"),
                        right_text="",
                        chunk_idx=chunk_idx,
                        tag="delete",
                    )
                )

        elif chunk.tag == "insert":
            for i, line in enumerate(chunk.right_lines):
                aligned.append(
                    AlignedLine(
                        left_lineno=None,
                        right_lineno=chunk.right_start + i + 1,
                        left_text="",
                        right_text=line.rstrip("\n"),
                        chunk_idx=chunk_idx,
                        tag="insert",
                    )
                )

    return aligned


def get_change_chunks(chunks: List[DiffChunk]) -> List[int]:
    """변경이 있는 청크의 인덱스 목록을 반환한다."""
    return [i for i, c in enumerate(chunks) if c.tag != "equal"]


def first_row_of_chunk(aligned: List[AlignedLine], chunk_idx: int) -> int:
    """aligned 목록에서 특정 chunk_idx 청크가 시작하는 행 번호를 반환한다."""
    for row_idx, line in enumerate(aligned):
        if line.chunk_idx == chunk_idx:
            return row_idx
    return 0

"""폴더 트리 비교 로직."""
from __future__ import annotations

import filecmp
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class FolderEntry:
    """비교 트리의 파일 또는 폴더 항목."""

    name: str
    rel_path: str          # 비교 루트로부터의 상대 경로
    is_dir: bool
    status: str            # 'same' | 'different' | 'left_only' | 'right_only'
    left_abs: Optional[Path] = None
    right_abs: Optional[Path] = None
    children: List["FolderEntry"] = field(default_factory=list)
    depth: int = 0


def compare_folders(left_root: Path, right_root: Path) -> List[FolderEntry]:
    """두 폴더 트리를 재귀적으로 비교하여 항목 목록을 반환한다."""
    return _compare_dir(left_root, right_root, "", 0)


def _compare_dir(
    left_path: Path, right_path: Path, rel: str, depth: int
) -> List[FolderEntry]:
    """단일 디렉터리 레벨을 비교한다."""
    left_items: set[str] = set()
    right_items: set[str] = set()

    if left_path.is_dir():
        left_items = {p.name for p in left_path.iterdir()}
    if right_path.is_dir():
        right_items = {p.name for p in right_path.iterdir()}

    all_names = sorted(
        left_items | right_items,
        key=lambda n: (
            _is_file(left_path / n, right_path / n, n, left_items, right_items),
            n.lower(),
        ),
    )

    entries: List[FolderEntry] = []
    for name in all_names:
        l_path = left_path / name
        r_path = right_path / name
        rel_path = f"{rel}/{name}".lstrip("/")

        l_exists = name in left_items
        r_exists = name in right_items

        if l_exists:
            is_dir = l_path.is_dir()
        else:
            is_dir = r_path.is_dir()

        if not l_exists:
            entry = FolderEntry(
                name=name,
                rel_path=rel_path,
                is_dir=is_dir,
                status="right_only",
                left_abs=None,
                right_abs=r_path,
                depth=depth,
            )
        elif not r_exists:
            entry = FolderEntry(
                name=name,
                rel_path=rel_path,
                is_dir=is_dir,
                status="left_only",
                left_abs=l_path,
                right_abs=None,
                depth=depth,
            )
        elif is_dir:
            children = _compare_dir(l_path, r_path, rel_path, depth + 1)
            has_diff = any(e.status != "same" for e in flatten_entries(children))
            status = "different" if has_diff else "same"
            entry = FolderEntry(
                name=name,
                rel_path=rel_path,
                is_dir=True,
                status=status,
                left_abs=l_path,
                right_abs=r_path,
                children=children,
                depth=depth,
            )
        else:
            try:
                same = filecmp.cmp(str(l_path), str(r_path), shallow=False)
                status = "same" if same else "different"
            except OSError:
                status = "different"
            entry = FolderEntry(
                name=name,
                rel_path=rel_path,
                is_dir=False,
                status=status,
                left_abs=l_path,
                right_abs=r_path,
                depth=depth,
            )

        entries.append(entry)

    return entries


def _is_file(
    l_path: Path, r_path: Path, name: str, left_set: set, right_set: set
) -> int:
    """정렬 키: 디렉터리=0(먼저), 파일=1."""
    if name in left_set and l_path.is_dir():
        return 0
    if name in right_set and r_path.is_dir():
        return 0
    return 1


def flatten_entries(
    entries: List[FolderEntry], expanded: Optional[set] = None
) -> List[FolderEntry]:
    """트리 항목을 평탄화한다. expanded가 None이면 모두 펼친다."""
    result: List[FolderEntry] = []
    for e in entries:
        result.append(e)
        if e.is_dir:
            if expanded is None or e.rel_path in expanded:
                result.extend(flatten_entries(e.children, expanded))
    return result

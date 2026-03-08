"""제외 설정 로드 및 적용 로직.

설정 파일: .folderdiff.toml
탐색 순서 (앞에서 먼저 발견된 파일 하나를 사용):
  1. 명시적으로 지정된 경로
  2. 왼쪽 비교 폴더
  3. 오른쪽 비교 폴더
  4. 현재 작업 디렉터리
  5. 홈 디렉터리 (~/.folderdiff.toml)
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import List, Optional

CONFIG_FILENAME = ".folderdiff.toml"


@dataclass
class ExcludeConfig:
    """제외 규칙 집합."""

    # 이름 정확 일치 (파일/폴더 모두)
    names: List[str] = field(default_factory=list)
    # 이름 glob 패턴 (파일/폴더 모두)
    patterns: List[str] = field(default_factory=list)
    # 폴더 이름만 정확 일치
    dirs: List[str] = field(default_factory=list)
    # 상대 경로 glob 패턴 (비교 루트 기준)
    path_patterns: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.names or self.patterns or self.dirs or self.path_patterns)


def load_config(
    explicit: Optional[Path] = None,
    left: Optional[Path] = None,
    right: Optional[Path] = None,
) -> ExcludeConfig:
    """우선순위에 따라 설정 파일을 탐색하여 로드한다.

    Args:
        explicit: 명시적으로 지정된 경로. 존재하지 않으면 오류.
        left:     왼쪽 비교 폴더.
        right:    오른쪽 비교 폴더.

    Returns:
        ExcludeConfig. 설정 파일을 찾지 못하면 빈 설정 반환.
    """
    candidates: List[Path] = []

    if explicit is not None:
        p = Path(explicit).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {p}")
        return _parse(p)

    if left is not None:
        candidates.append(Path(left) / CONFIG_FILENAME)
    if right is not None:
        candidates.append(Path(right) / CONFIG_FILENAME)
    candidates.append(Path.cwd() / CONFIG_FILENAME)
    candidates.append(Path.home() / CONFIG_FILENAME)

    for path in candidates:
        if path.exists():
            return _parse(path)

    return ExcludeConfig()


def _parse(path: Path) -> ExcludeConfig:
    """TOML 파일을 파싱하여 ExcludeConfig 를 반환한다."""
    with open(path, "rb") as f:
        data = tomllib.load(f)

    excl = data.get("exclude", {})
    return ExcludeConfig(
        names=excl.get("names", []),
        patterns=excl.get("patterns", []),
        dirs=excl.get("dirs", []),
        path_patterns=excl.get("path_patterns", []),
    )


def should_exclude(
    name: str,
    rel_path: str,
    is_dir: bool,
    config: ExcludeConfig,
) -> bool:
    """항목이 제외 대상인지 판단한다.

    Args:
        name:     파일/폴더 이름 (경로 아님).
        rel_path: 비교 루트 기준 상대 경로.
        is_dir:   폴더 여부.
        config:   적용할 ExcludeConfig.

    Returns:
        True 이면 제외.
    """
    if config.is_empty:
        return False

    # 1. 이름 정확 일치
    if name in config.names:
        return True

    # 2. 폴더-전용 이름 정확 일치
    if is_dir and name in config.dirs:
        return True

    # 3. 이름 glob 패턴
    for pat in config.patterns:
        if fnmatch(name, pat):
            return True

    # 4. 상대 경로 glob 패턴
    for pat in config.path_patterns:
        if fnmatch(rel_path, pat):
            return True

    return False

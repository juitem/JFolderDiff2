"""pytest 공통 픽스처."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def left_root(fixtures_dir: Path) -> Path:
    return fixtures_dir / "left"


@pytest.fixture
def right_root(fixtures_dir: Path) -> Path:
    return fixtures_dir / "right"


@pytest.fixture
def simple_left_lines():
    return [
        "First line\n",
        "Second line\n",
        "Third line\n",
    ]


@pytest.fixture
def simple_right_lines():
    return [
        "First line\n",
        "CHANGED second line\n",
        "Third line\n",
        "New fourth line\n",
    ]

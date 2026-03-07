"""pytest 공통 픽스처 — FastAPI TestClient 포함."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# gui/backend 를 import 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from gui.backend.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def tmp_left(tmp_path: Path) -> Path:
    d = tmp_path / "left"
    d.mkdir()
    (d / "same.txt").write_text("same content\n")
    (d / "modified.txt").write_text("left version\n")
    (d / "left_only.txt").write_text("only on left\n")
    sub = d / "subdir"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested left\n")
    return d


@pytest.fixture
def tmp_right(tmp_path: Path) -> Path:
    d = tmp_path / "right"
    d.mkdir()
    (d / "same.txt").write_text("same content\n")
    (d / "modified.txt").write_text("right version\n")
    (d / "right_only.txt").write_text("only on right\n")
    sub = d / "subdir"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested right\n")
    return d

"""GET /api/browse 테스트."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient


class TestBrowseApi:
    def test_browse_existing_directory(self, client: TestClient, tmp_path: Path):
        res = client.get("/api/browse", params={"path": str(tmp_path)})
        assert res.status_code == 200
        data = res.json()
        assert data["path"] == str(tmp_path)

    def test_browse_returns_entries(self, client: TestClient, tmp_path: Path):
        (tmp_path / "a_dir").mkdir()
        (tmp_path / "b_file.txt").write_text("hello")
        res = client.get("/api/browse", params={"path": str(tmp_path)})
        data = res.json()
        names = [e["name"] for e in data["entries"]]
        assert "a_dir" in names
        assert "b_file.txt" in names

    def test_directories_listed_before_files(self, client: TestClient, tmp_path: Path):
        (tmp_path / "z_dir").mkdir()
        (tmp_path / "a_file.txt").write_text("x")
        res = client.get("/api/browse", params={"path": str(tmp_path)})
        entries = res.json()["entries"]
        dirs  = [e for e in entries if e["is_dir"]]
        files = [e for e in entries if not e["is_dir"]]
        if dirs and files:
            assert entries.index(dirs[0]) < entries.index(files[0])

    def test_entry_has_required_fields(self, client: TestClient, tmp_path: Path):
        (tmp_path / "file.txt").write_text("content")
        res = client.get("/api/browse", params={"path": str(tmp_path)})
        entry = res.json()["entries"][0]
        assert "name" in entry
        assert "path" in entry
        assert "is_dir" in entry
        assert "size" in entry
        assert "modified" in entry

    def test_file_entry_has_size(self, client: TestClient, tmp_path: Path):
        f = tmp_path / "sized.txt"
        f.write_text("12345")
        res = client.get("/api/browse", params={"path": str(tmp_path)})
        entry = next(e for e in res.json()["entries"] if e["name"] == "sized.txt")
        assert entry["size"] == 5
        assert entry["is_dir"] is False

    def test_directory_entry_has_null_size(self, client: TestClient, tmp_path: Path):
        (tmp_path / "mydir").mkdir()
        res = client.get("/api/browse", params={"path": str(tmp_path)})
        entry = next(e for e in res.json()["entries"] if e["name"] == "mydir")
        assert entry["size"] is None
        assert entry["is_dir"] is True

    def test_returns_parent_path(self, client: TestClient, tmp_path: Path):
        subdir = tmp_path / "child"
        subdir.mkdir()
        res = client.get("/api/browse", params={"path": str(subdir)})
        data = res.json()
        assert data["parent"] == str(tmp_path)

    def test_browse_nonexistent_path_returns_400(self, client: TestClient, tmp_path: Path):
        res = client.get("/api/browse", params={"path": str(tmp_path / "nonexistent")})
        assert res.status_code == 400

    def test_browse_file_path_returns_400(self, client: TestClient, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_text("x")
        res = client.get("/api/browse", params={"path": str(f)})
        assert res.status_code == 400

    def test_browse_home_tilde_expands(self, client: TestClient):
        res = client.get("/api/browse", params={"path": "~"})
        assert res.status_code == 200
        assert res.json()["path"] != "~"

    def test_empty_directory(self, client: TestClient, tmp_path: Path):
        empty = tmp_path / "empty"
        empty.mkdir()
        res = client.get("/api/browse", params={"path": str(empty)})
        assert res.status_code == 200
        assert res.json()["entries"] == []

"""GET /api/compare 및 GET /api/diff 테스트."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


class TestCompareFolderApi:
    def test_basic_compare_returns_200(self, client, tmp_left, tmp_right):
        res = client.get("/api/compare", params={"left": str(tmp_left), "right": str(tmp_right)})
        assert res.status_code == 200

    def test_compare_response_structure(self, client, tmp_left, tmp_right):
        data = client.get("/api/compare", params={"left": str(tmp_left), "right": str(tmp_right)}).json()
        assert "left" in data
        assert "right" in data
        assert "stats" in data
        assert "entries" in data

    def test_stats_counts_are_correct(self, client, tmp_left, tmp_right):
        data = client.get("/api/compare", params={"left": str(tmp_left), "right": str(tmp_right)}).json()
        stats = data["stats"]
        assert stats["same"] >= 1        # same.txt
        assert stats["different"] >= 1   # modified.txt
        assert stats["left_only"] >= 1   # left_only.txt
        assert stats["right_only"] >= 1  # right_only.txt

    def test_entry_statuses_are_valid(self, client, tmp_left, tmp_right):
        data = client.get("/api/compare", params={"left": str(tmp_left), "right": str(tmp_right)}).json()
        valid_statuses = {"same", "different", "left_only", "right_only"}
        for entry in data["entries"]:
            assert entry["status"] in valid_statuses

    def test_entry_has_required_fields(self, client, tmp_left, tmp_right):
        data = client.get("/api/compare", params={"left": str(tmp_left), "right": str(tmp_right)}).json()
        for entry in data["entries"]:
            assert "name" in entry
            assert "rel_path" in entry
            assert "is_dir" in entry
            assert "status" in entry
            assert "depth" in entry
            assert "children" in entry

    def test_same_file_has_same_status(self, client, tmp_left, tmp_right):
        data = client.get("/api/compare", params={"left": str(tmp_left), "right": str(tmp_right)}).json()
        same_entry = next((e for e in data["entries"] if e["name"] == "same.txt"), None)
        assert same_entry is not None
        assert same_entry["status"] == "same"

    def test_modified_file_has_different_status(self, client, tmp_left, tmp_right):
        data = client.get("/api/compare", params={"left": str(tmp_left), "right": str(tmp_right)}).json()
        mod_entry = next((e for e in data["entries"] if e["name"] == "modified.txt"), None)
        assert mod_entry is not None
        assert mod_entry["status"] == "different"

    def test_left_only_file_has_null_right_abs(self, client, tmp_left, tmp_right):
        data = client.get("/api/compare", params={"left": str(tmp_left), "right": str(tmp_right)}).json()
        lo = next((e for e in data["entries"] if e["name"] == "left_only.txt"), None)
        assert lo is not None
        assert lo["right_abs"] is None
        assert lo["left_abs"] is not None

    def test_right_only_file_has_null_left_abs(self, client, tmp_left, tmp_right):
        data = client.get("/api/compare", params={"left": str(tmp_left), "right": str(tmp_right)}).json()
        ro = next((e for e in data["entries"] if e["name"] == "right_only.txt"), None)
        assert ro is not None
        assert ro["left_abs"] is None
        assert ro["right_abs"] is not None

    def test_subdir_has_children(self, client, tmp_left, tmp_right):
        data = client.get("/api/compare", params={"left": str(tmp_left), "right": str(tmp_right)}).json()
        subdir = next((e for e in data["entries"] if e["is_dir"]), None)
        assert subdir is not None
        assert isinstance(subdir["children"], list)

    def test_invalid_left_returns_400(self, client, tmp_right):
        res = client.get("/api/compare", params={"left": "/nonexistent", "right": str(tmp_right)})
        assert res.status_code == 400

    def test_invalid_right_returns_400(self, client, tmp_left):
        res = client.get("/api/compare", params={"left": str(tmp_left), "right": "/nonexistent"})
        assert res.status_code == 400

    def test_same_folders_all_stats_are_same(self, client, tmp_path):
        left = tmp_path / "a"; left.mkdir()
        right = tmp_path / "b"; right.mkdir()
        (left / "x.txt").write_text("same")
        (right / "x.txt").write_text("same")
        data = client.get("/api/compare", params={"left": str(left), "right": str(right)}).json()
        stats = data["stats"]
        assert stats["different"] == 0
        assert stats["left_only"] == 0
        assert stats["right_only"] == 0
        assert stats["same"] >= 1


class TestDiffFileApi:
    def test_diff_two_files(self, client, tmp_left, tmp_right):
        l = str(tmp_left / "modified.txt")
        r = str(tmp_right / "modified.txt")
        res = client.get("/api/diff", params={"left": l, "right": r})
        assert res.status_code == 200

    def test_diff_response_structure(self, client, tmp_left, tmp_right):
        l = str(tmp_left / "modified.txt")
        r = str(tmp_right / "modified.txt")
        data = client.get("/api/diff", params={"left": l, "right": r}).json()
        assert "change_count" in data
        assert "chunks" in data
        assert "aligned" in data
        assert "error" in data

    def test_diff_same_files_has_zero_changes(self, client, tmp_left, tmp_right):
        l = str(tmp_left / "same.txt")
        r = str(tmp_right / "same.txt")
        data = client.get("/api/diff", params={"left": l, "right": r}).json()
        assert data["change_count"] == 0
        assert data["error"] is None

    def test_diff_modified_files_has_changes(self, client, tmp_left, tmp_right):
        l = str(tmp_left / "modified.txt")
        r = str(tmp_right / "modified.txt")
        data = client.get("/api/diff", params={"left": l, "right": r}).json()
        assert data["change_count"] >= 1

    def test_aligned_lines_have_required_fields(self, client, tmp_left, tmp_right):
        l = str(tmp_left / "modified.txt")
        r = str(tmp_right / "modified.txt")
        data = client.get("/api/diff", params={"left": l, "right": r}).json()
        for row in data["aligned"]:
            assert "left_text" in row
            assert "right_text" in row
            assert "tag" in row
            assert "chunk_idx" in row

    def test_chunks_have_valid_tags(self, client, tmp_left, tmp_right):
        l = str(tmp_left / "modified.txt")
        r = str(tmp_right / "modified.txt")
        data = client.get("/api/diff", params={"left": l, "right": r}).json()
        valid_tags = {"equal", "replace", "insert", "delete"}
        for chunk in data["chunks"]:
            assert chunk["tag"] in valid_tags

    def test_diff_left_only_file(self, client, tmp_left):
        """한쪽 파일만 있을 때 (오른쪽 없음)."""
        l = str(tmp_left / "left_only.txt")
        data = client.get("/api/diff", params={"left": l}).json()
        # 오른쪽이 없으면 왼쪽 전체가 delete
        assert data["change_count"] >= 1 or data["error"] is not None

    def test_diff_binary_file_returns_error(self, client, tmp_path):
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\x00\x01\x02\x03")
        data = client.get("/api/diff", params={"left": str(f)}).json()
        assert data["error"] is not None
        assert data["change_count"] == 0

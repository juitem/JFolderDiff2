"""POST /api/merge 테스트."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


class TestMergeApi:
    def _post(self, client, left, right, decisions):
        return client.post("/api/merge", json={
            "left_path": str(left) if left else None,
            "right_path": str(right) if right else None,
            "decisions": decisions,
        })

    def test_merge_left_to_right(self, client, tmp_path):
        left  = tmp_path / "left.txt";  left.write_text("left content\n")
        right = tmp_path / "right.txt"; right.write_text("right content\n")

        # 먼저 diff로 청크 인덱스를 확인
        diff = client.get("/api/diff", params={"left": str(left), "right": str(right)}).json()
        change_idx = next(i for i, c in enumerate(diff["chunks"]) if c["tag"] != "equal")

        res = self._post(client, left, right, {str(change_idx): "left"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert str(right) in data["saved_files"]
        assert right.read_text() == "left content\n"

    def test_merge_right_to_left(self, client, tmp_path):
        left  = tmp_path / "left.txt";  left.write_text("left content\n")
        right = tmp_path / "right.txt"; right.write_text("right content\n")

        diff = client.get("/api/diff", params={"left": str(left), "right": str(right)}).json()
        change_idx = next(i for i, c in enumerate(diff["chunks"]) if c["tag"] != "equal")

        res = self._post(client, left, right, {str(change_idx): "right"})
        assert res.status_code == 200
        assert left.read_text() == "right content\n"

    def test_empty_decisions_returns_no_changes(self, client, tmp_path):
        left  = tmp_path / "l.txt"; left.write_text("a\n")
        right = tmp_path / "r.txt"; right.write_text("b\n")
        res = self._post(client, left, right, {})
        assert res.status_code == 200
        assert res.json()["success"] is False

    def test_invalid_path_returns_400(self, client, tmp_path):
        left = tmp_path / "nonexistent.txt"
        right = tmp_path / "r.txt"; right.write_text("x\n")
        res = self._post(client, left, right, {"0": "left"})
        assert res.status_code == 400

    def test_invalid_chunk_index_returns_400(self, client, tmp_path):
        left  = tmp_path / "l.txt"; left.write_text("a\n")
        right = tmp_path / "r.txt"; right.write_text("b\n")
        res = self._post(client, left, right, {"999": "left"})
        assert res.status_code == 400

    def test_invalid_decision_value_returns_400(self, client, tmp_path):
        left  = tmp_path / "l.txt"; left.write_text("a\n")
        right = tmp_path / "r.txt"; right.write_text("b\n")
        res = self._post(client, left, right, {"0": "invalid_direction"})
        assert res.status_code == 400

    def test_merge_preserves_equal_lines(self, client, tmp_path):
        left  = tmp_path / "l.txt"; left.write_text("header\nleft line\nfooter\n")
        right = tmp_path / "r.txt"; right.write_text("header\nright line\nfooter\n")

        diff = client.get("/api/diff", params={"left": str(left), "right": str(right)}).json()
        change_idx = next(i for i, c in enumerate(diff["chunks"]) if c["tag"] != "equal")

        self._post(client, left, right, {str(change_idx): "left"})

        content = right.read_text()
        assert "header\n" in content
        assert "footer\n" in content
        assert "left line\n" in content

    def test_merge_multiple_chunks(self, client, tmp_path):
        left  = tmp_path / "l.txt"; left.write_text("A\nB\nC\nD\n")
        right = tmp_path / "r.txt"; right.write_text("a\nB\nc\nD\n")

        diff = client.get("/api/diff", params={"left": str(left), "right": str(right)}).json()
        changes = [str(i) for i, c in enumerate(diff["chunks"]) if c["tag"] != "equal"]

        decisions = {idx: "left" for idx in changes}
        res = self._post(client, left, right, decisions)
        assert res.status_code == 200
        assert right.read_text() == "A\nB\nC\nD\n"

    def test_response_contains_saved_files(self, client, tmp_path):
        left  = tmp_path / "l.txt"; left.write_text("left\n")
        right = tmp_path / "r.txt"; right.write_text("right\n")

        diff = client.get("/api/diff", params={"left": str(left), "right": str(right)}).json()
        change_idx = next(i for i, c in enumerate(diff["chunks"]) if c["tag"] != "equal")

        res = self._post(client, left, right, {str(change_idx): "left"})
        data = res.json()
        assert isinstance(data["saved_files"], list)
        assert len(data["saved_files"]) > 0

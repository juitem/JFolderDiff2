"""folder_diff 모듈 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.models.folder_diff import FolderEntry, compare_folders, flatten_entries


# ── compare_folders ───────────────────────────────────────────────────────────


class TestCompareFolders:
    def test_identical_single_file(self, tmp_path: Path):
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "file.txt").write_text("content")
        (right / "file.txt").write_text("content")

        entries = compare_folders(left, right)
        assert len(entries) == 1
        assert entries[0].name == "file.txt"
        assert entries[0].status == "same"
        assert entries[0].is_dir is False

    def test_different_single_file(self, tmp_path: Path):
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "file.txt").write_text("left content")
        (right / "file.txt").write_text("right content")

        entries = compare_folders(left, right)
        assert entries[0].status == "different"

    def test_left_only_file(self, tmp_path: Path):
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (left / "only_left.txt").write_text("exists only on left")

        entries = compare_folders(left, right)
        assert len(entries) == 1
        assert entries[0].status == "left_only"
        assert entries[0].left_abs is not None
        assert entries[0].right_abs is None

    def test_right_only_file(self, tmp_path: Path):
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()
        (right / "only_right.txt").write_text("exists only on right")

        entries = compare_folders(left, right)
        assert len(entries) == 1
        assert entries[0].status == "right_only"
        assert entries[0].left_abs is None
        assert entries[0].right_abs is not None

    def test_mixed_statuses(self, tmp_path: Path):
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        (left / "same.txt").write_text("same")
        (right / "same.txt").write_text("same")
        (left / "modified.txt").write_text("left")
        (right / "modified.txt").write_text("right")
        (left / "left_only.txt").write_text("left only")
        (right / "right_only.txt").write_text("right only")

        entries = compare_folders(left, right)
        statuses = {e.name: e.status for e in entries}
        assert statuses["same.txt"] == "same"
        assert statuses["modified.txt"] == "different"
        assert statuses["left_only.txt"] == "left_only"
        assert statuses["right_only.txt"] == "right_only"

    def test_empty_folders(self, tmp_path: Path):
        left = tmp_path / "left"
        right = tmp_path / "right"
        left.mkdir()
        right.mkdir()

        entries = compare_folders(left, right)
        assert entries == []

    def test_nested_directory_same(self, tmp_path: Path):
        left = tmp_path / "left"
        right = tmp_path / "right"
        (left / "sub").mkdir(parents=True)
        (right / "sub").mkdir(parents=True)
        (left / "sub" / "file.txt").write_text("same content")
        (right / "sub" / "file.txt").write_text("same content")

        entries = compare_folders(left, right)
        assert len(entries) == 1
        assert entries[0].is_dir is True
        assert entries[0].status == "same"
        assert len(entries[0].children) == 1
        assert entries[0].children[0].status == "same"

    def test_nested_directory_different(self, tmp_path: Path):
        left = tmp_path / "left"
        right = tmp_path / "right"
        (left / "sub").mkdir(parents=True)
        (right / "sub").mkdir(parents=True)
        (left / "sub" / "file.txt").write_text("left content")
        (right / "sub" / "file.txt").write_text("right content")

        entries = compare_folders(left, right)
        assert entries[0].is_dir is True
        assert entries[0].status == "different"

    def test_directories_sorted_before_files(self, tmp_path: Path):
        left = tmp_path / "left"
        right = tmp_path / "right"
        (left / "subdir").mkdir(parents=True)
        (right / "subdir").mkdir(parents=True)
        (left / "aaa.txt").write_text("file")
        (right / "aaa.txt").write_text("file")

        entries = compare_folders(left, right)
        assert entries[0].is_dir is True  # 디렉터리가 먼저
        assert entries[1].is_dir is False

    def test_fixture_folders(self, left_root: Path, right_root: Path):
        """실제 픽스처 폴더를 사용한 통합 테스트."""
        entries = compare_folders(left_root, right_root)
        flat = flatten_entries(entries)
        names = {e.name for e in flat}
        assert "same.txt" in names
        assert "modified.txt" in names
        assert "left_only.txt" in names
        assert "right_only.txt" in names


# ── flatten_entries ───────────────────────────────────────────────────────────


class TestFlattenEntries:
    def _make_tree(self) -> list[FolderEntry]:
        child1 = FolderEntry("child1.txt", "dir/child1.txt", False, "same", depth=1)
        child2 = FolderEntry("child2.txt", "dir/child2.txt", False, "different", depth=1)
        parent = FolderEntry(
            "dir", "dir", True, "different",
            children=[child1, child2], depth=0
        )
        return [parent]

    def test_none_expanded_flattens_all(self):
        tree = self._make_tree()
        flat = flatten_entries(tree, expanded=None)
        assert len(flat) == 3  # parent + 2 children

    def test_empty_expanded_hides_children(self):
        tree = self._make_tree()
        flat = flatten_entries(tree, expanded=set())
        assert len(flat) == 1  # only parent

    def test_expanded_rel_path_shows_children(self):
        tree = self._make_tree()
        flat = flatten_entries(tree, expanded={"dir"})
        assert len(flat) == 3

    def test_order_is_parent_before_children(self):
        tree = self._make_tree()
        flat = flatten_entries(tree, expanded=None)
        assert flat[0].name == "dir"
        assert flat[1].name == "child1.txt"

    def test_entry_depth_preserved(self):
        tree = self._make_tree()
        flat = flatten_entries(tree, expanded=None)
        assert flat[0].depth == 0
        assert flat[1].depth == 1
        assert flat[2].depth == 1

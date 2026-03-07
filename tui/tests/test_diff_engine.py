"""diff_engine 모듈 테스트."""
from __future__ import annotations

import pytest

from src.models.diff_engine import (
    AlignedLine,
    DiffChunk,
    build_aligned_lines,
    compute_diff,
    first_row_of_chunk,
    get_change_chunks,
)


# ── compute_diff ──────────────────────────────────────────────────────────────


class TestComputeDiff:
    def test_equal_files_returns_one_equal_chunk(self):
        lines = ["line1\n", "line2\n", "line3\n"]
        chunks = compute_diff(lines, lines)
        assert len(chunks) == 1
        assert chunks[0].tag == "equal"
        assert chunks[0].left_lines == lines
        assert chunks[0].right_lines == lines

    def test_empty_files_returns_empty(self):
        chunks = compute_diff([], [])
        assert chunks == []

    def test_left_empty_right_has_lines(self):
        right = ["a\n", "b\n"]
        chunks = compute_diff([], right)
        assert len(chunks) == 1
        assert chunks[0].tag == "insert"
        assert chunks[0].right_lines == right

    def test_right_empty_left_has_lines(self):
        left = ["a\n", "b\n"]
        chunks = compute_diff(left, [])
        assert len(chunks) == 1
        assert chunks[0].tag == "delete"
        assert chunks[0].left_lines == left

    def test_single_line_replacement(self):
        left = ["hello\n"]
        right = ["world\n"]
        chunks = compute_diff(left, right)
        change_idx = get_change_chunks(chunks)
        assert len(change_idx) == 1
        assert chunks[change_idx[0]].tag == "replace"

    def test_insertion_in_middle(self):
        left = ["a\n", "c\n"]
        right = ["a\n", "b\n", "c\n"]
        chunks = compute_diff(left, right)
        tags = [c.tag for c in chunks]
        assert "insert" in tags

    def test_deletion_in_middle(self):
        left = ["a\n", "b\n", "c\n"]
        right = ["a\n", "c\n"]
        chunks = compute_diff(left, right)
        tags = [c.tag for c in chunks]
        assert "delete" in tags

    def test_multiple_changes(self, simple_left_lines, simple_right_lines):
        chunks = compute_diff(simple_left_lines, simple_right_lines)
        change_idx = get_change_chunks(chunks)
        assert len(change_idx) >= 1

    def test_chunk_indices_are_consistent(self):
        left = ["a\n", "b\n", "c\n", "d\n"]
        right = ["a\n", "X\n", "c\n", "Y\n"]
        chunks = compute_diff(left, right)
        for chunk in chunks:
            assert chunk.left_end >= chunk.left_start
            assert chunk.right_end >= chunk.right_start
            assert len(chunk.left_lines) == chunk.left_end - chunk.left_start
            assert len(chunk.right_lines) == chunk.right_end - chunk.right_start

    def test_all_chunks_cover_full_file(self):
        left = ["a\n", "b\n", "c\n"]
        right = ["a\n", "X\n", "Y\n", "c\n"]
        chunks = compute_diff(left, right)
        left_pos = 0
        right_pos = 0
        for chunk in chunks:
            assert chunk.left_start == left_pos
            assert chunk.right_start == right_pos
            left_pos = chunk.left_end
            right_pos = chunk.right_end
        assert left_pos == len(left)
        assert right_pos == len(right)


# ── get_change_chunks ─────────────────────────────────────────────────────────


class TestGetChangeChunks:
    def test_no_changes_returns_empty(self):
        lines = ["a\n", "b\n"]
        chunks = compute_diff(lines, lines)
        assert get_change_chunks(chunks) == []

    def test_single_change(self):
        left = ["a\n"]
        right = ["b\n"]
        chunks = compute_diff(left, right)
        assert len(get_change_chunks(chunks)) == 1

    def test_multiple_changes(self):
        left = ["a\n", "b\n", "c\n", "d\n"]
        right = ["A\n", "b\n", "C\n", "d\n"]
        chunks = compute_diff(left, right)
        change_idx = get_change_chunks(chunks)
        assert len(change_idx) >= 2


# ── build_aligned_lines ───────────────────────────────────────────────────────


class TestBuildAlignedLines:
    def test_equal_chunk_produces_paired_lines(self):
        left = ["a\n", "b\n"]
        right = ["a\n", "b\n"]
        chunks = compute_diff(left, right)
        aligned = build_aligned_lines(chunks)
        assert len(aligned) == 2
        assert all(a.tag == "equal" for a in aligned)
        assert aligned[0].left_lineno == 1
        assert aligned[0].right_lineno == 1
        assert aligned[1].left_lineno == 2
        assert aligned[1].right_lineno == 2

    def test_delete_chunk_has_none_right_lineno(self):
        left = ["a\n", "b\n", "c\n"]
        right = ["a\n", "c\n"]
        chunks = compute_diff(left, right)
        aligned = build_aligned_lines(chunks)
        delete_rows = [a for a in aligned if a.tag == "delete"]
        assert len(delete_rows) == 1
        assert delete_rows[0].left_lineno == 2
        assert delete_rows[0].right_lineno is None
        assert delete_rows[0].right_text == ""

    def test_insert_chunk_has_none_left_lineno(self):
        left = ["a\n", "c\n"]
        right = ["a\n", "b\n", "c\n"]
        chunks = compute_diff(left, right)
        aligned = build_aligned_lines(chunks)
        insert_rows = [a for a in aligned if a.tag == "insert"]
        assert len(insert_rows) == 1
        assert insert_rows[0].left_lineno is None
        assert insert_rows[0].right_lineno == 2
        assert insert_rows[0].left_text == ""

    def test_replace_chunk_aligns_by_max_length(self):
        # left has 3 lines, right has 1 line in the changed region
        left = ["a\n", "X\n", "Y\n", "Z\n", "b\n"]
        right = ["a\n", "W\n", "b\n"]
        chunks = compute_diff(left, right)
        aligned = build_aligned_lines(chunks)
        replace_rows = [a for a in aligned if a.tag == "replace"]
        # replace region should have max(3, 1) = 3 rows
        assert len(replace_rows) == 3
        # First row has both sides
        assert replace_rows[0].left_lineno is not None
        assert replace_rows[0].right_lineno is not None
        # Extra rows have None on right side
        assert replace_rows[1].right_lineno is None
        assert replace_rows[2].right_lineno is None

    def test_newlines_stripped_from_text(self):
        left = ["hello\n"]
        right = ["world\n"]
        chunks = compute_diff(left, right)
        aligned = build_aligned_lines(chunks)
        for row in aligned:
            assert "\n" not in row.left_text
            assert "\n" not in row.right_text

    def test_chunk_idx_matches_chunk_position(self):
        left = ["a\n", "b\n", "c\n"]
        right = ["a\n", "X\n", "c\n"]
        chunks = compute_diff(left, right)
        aligned = build_aligned_lines(chunks)
        for row in aligned:
            assert 0 <= row.chunk_idx < len(chunks)
            assert row.tag == chunks[row.chunk_idx].tag


# ── first_row_of_chunk ────────────────────────────────────────────────────────


class TestFirstRowOfChunk:
    def test_returns_correct_row_for_first_chunk(self):
        left = ["a\n", "b\n"]
        right = ["X\n", "b\n"]
        chunks = compute_diff(left, right)
        aligned = build_aligned_lines(chunks)
        row = first_row_of_chunk(aligned, 0)
        assert row == 0

    def test_returns_correct_row_for_later_chunk(self):
        left = ["a\n", "b\n", "c\n"]
        right = ["a\n", "X\n", "c\n"]
        chunks = compute_diff(left, right)
        aligned = build_aligned_lines(chunks)
        change_idx = get_change_chunks(chunks)[0]
        row = first_row_of_chunk(aligned, change_idx)
        assert aligned[row].chunk_idx == change_idx

    def test_returns_0_for_missing_chunk(self):
        chunks = compute_diff(["a\n"], ["a\n"])
        aligned = build_aligned_lines(chunks)
        assert first_row_of_chunk(aligned, 999) == 0

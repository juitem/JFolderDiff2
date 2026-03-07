"""merge_state 모듈 테스트."""
from __future__ import annotations

import pytest

from src.models.diff_engine import DiffChunk, compute_diff, get_change_chunks
from src.models.merge_state import MergeDecision, MergeState


def _make_chunks(left_lines, right_lines):
    return compute_diff(left_lines, right_lines)


def _change_idx(chunks):
    return get_change_chunks(chunks)


# ── MergeState 기본 동작 ──────────────────────────────────────────────────────


class TestMergeStateBasics:
    def test_initial_state_is_none(self):
        state = MergeState(5)
        for i in range(5):
            assert state.get(i) == MergeDecision.NONE

    def test_set_and_get_left(self):
        state = MergeState(3)
        state.set(1, MergeDecision.LEFT)
        assert state.get(1) == MergeDecision.LEFT

    def test_set_and_get_right(self):
        state = MergeState(3)
        state.set(2, MergeDecision.RIGHT)
        assert state.get(2) == MergeDecision.RIGHT

    def test_set_none_removes_decision(self):
        state = MergeState(3)
        state.set(0, MergeDecision.LEFT)
        state.set(0, MergeDecision.NONE)
        assert state.get(0) == MergeDecision.NONE
        assert not state.has_any_decision()

    def test_has_any_decision_false_initially(self):
        assert not MergeState(3).has_any_decision()

    def test_has_any_decision_true_after_set(self):
        state = MergeState(3)
        state.set(0, MergeDecision.LEFT)
        assert state.has_any_decision()

    def test_clear_removes_all(self):
        state = MergeState(3)
        state.set(0, MergeDecision.LEFT)
        state.set(1, MergeDecision.RIGHT)
        state.clear()
        assert not state.has_any_decision()


# ── is_modified 플래그 ────────────────────────────────────────────────────────


class TestModifiedFlags:
    def test_left_decision_marks_right_modified(self):
        state = MergeState(3)
        state.set(0, MergeDecision.LEFT)
        assert state.is_right_modified() is True
        assert state.is_left_modified() is False

    def test_right_decision_marks_left_modified(self):
        state = MergeState(3)
        state.set(0, MergeDecision.RIGHT)
        assert state.is_left_modified() is True
        assert state.is_right_modified() is False

    def test_no_decision_not_modified(self):
        state = MergeState(3)
        assert state.is_left_modified() is False
        assert state.is_right_modified() is False


# ── accept_all ────────────────────────────────────────────────────────────────


class TestAcceptAll:
    def _setup(self):
        left = ["a\n", "b\n", "c\n"]
        right = ["A\n", "b\n", "C\n"]
        chunks = _make_chunks(left, right)
        changes = _change_idx(chunks)
        return MergeState(len(chunks)), chunks, changes

    def test_accept_all_left_sets_left_for_all_changes(self):
        state, chunks, changes = self._setup()
        state.accept_all_left(changes)
        for idx in changes:
            assert state.get(idx) == MergeDecision.LEFT

    def test_accept_all_right_sets_right_for_all_changes(self):
        state, chunks, changes = self._setup()
        state.accept_all_right(changes)
        for idx in changes:
            assert state.get(idx) == MergeDecision.RIGHT


# ── apply_to_right ────────────────────────────────────────────────────────────


class TestApplyToRight:
    def test_no_decision_keeps_right_content(self):
        left = ["a\n", "b\n"]
        right = ["X\n", "b\n"]
        chunks = _make_chunks(left, right)
        state = MergeState(len(chunks))
        result = state.apply_to_right(chunks)
        assert result == right

    def test_left_decision_replaces_right_with_left(self):
        left = ["a\n", "b\n"]
        right = ["X\n", "b\n"]
        chunks = _make_chunks(left, right)
        changes = _change_idx(chunks)
        state = MergeState(len(chunks))
        state.set(changes[0], MergeDecision.LEFT)
        result = state.apply_to_right(chunks)
        assert result == ["a\n", "b\n"]

    def test_right_decision_keeps_right_for_right(self):
        left = ["a\n", "b\n"]
        right = ["X\n", "b\n"]
        chunks = _make_chunks(left, right)
        changes = _change_idx(chunks)
        state = MergeState(len(chunks))
        state.set(changes[0], MergeDecision.RIGHT)
        result = state.apply_to_right(chunks)
        assert result == right

    def test_equal_content_is_always_preserved(self):
        left = ["same\n", "diff_left\n", "same\n"]
        right = ["same\n", "diff_right\n", "same\n"]
        chunks = _make_chunks(left, right)
        changes = _change_idx(chunks)
        state = MergeState(len(chunks))
        state.set(changes[0], MergeDecision.LEFT)
        result = state.apply_to_right(chunks)
        assert result[0] == "same\n"
        assert result[-1] == "same\n"
        assert result[1] == "diff_left\n"

    def test_insert_accepted_from_left_means_empty_in_right(self):
        """right_only 줄을 왼쪽(없음)으로 채택하면 해당 줄이 사라진다."""
        left = ["a\n", "c\n"]
        right = ["a\n", "b\n", "c\n"]
        chunks = _make_chunks(left, right)
        changes = _change_idx(chunks)
        state = MergeState(len(chunks))
        state.set(changes[0], MergeDecision.LEFT)
        result = state.apply_to_right(chunks)
        assert result == ["a\n", "c\n"]


# ── apply_to_left ─────────────────────────────────────────────────────────────


class TestApplyToLeft:
    def test_no_decision_keeps_left_content(self):
        left = ["a\n", "b\n"]
        right = ["X\n", "b\n"]
        chunks = _make_chunks(left, right)
        state = MergeState(len(chunks))
        result = state.apply_to_left(chunks)
        assert result == left

    def test_right_decision_replaces_left_with_right(self):
        left = ["a\n", "b\n"]
        right = ["X\n", "b\n"]
        chunks = _make_chunks(left, right)
        changes = _change_idx(chunks)
        state = MergeState(len(chunks))
        state.set(changes[0], MergeDecision.RIGHT)
        result = state.apply_to_left(chunks)
        assert result == ["X\n", "b\n"]

    def test_mixed_decisions_apply_correctly(self):
        left = ["A\n", "B\n", "C\n", "D\n"]
        right = ["a\n", "B\n", "c\n", "D\n"]
        chunks = _make_chunks(left, right)
        changes = _change_idx(chunks)
        state = MergeState(len(chunks))
        # 첫 번째 변경: 오른쪽 채택 → 왼쪽 파일에 'a\n' 사용
        state.set(changes[0], MergeDecision.RIGHT)
        # 두 번째 변경: 결정 없음 → 왼쪽 원본 유지 'C\n'
        result = state.apply_to_left(chunks)
        assert "a\n" in result   # 오른쪽 채택됨
        assert "C\n" in result   # 결정 없으면 왼쪽 유지


# ── 통합 시나리오 ─────────────────────────────────────────────────────────────


class TestIntegration:
    def test_full_merge_workflow(self):
        """전체 머지 워크플로우: diff → 결정 → 적용."""
        left = ["header\n", "old line\n", "footer\n"]
        right = ["header\n", "new line\n", "footer\n"]

        chunks = _make_chunks(left, right)
        changes = _change_idx(chunks)
        assert len(changes) == 1

        state = MergeState(len(chunks))
        assert not state.has_any_decision()

        # 왼쪽 채택 → 오른쪽 파일이 왼쪽 내용을 가져야 한다
        state.set(changes[0], MergeDecision.LEFT)
        right_result = state.apply_to_right(chunks)
        assert right_result == left

        # 취소 후 오른쪽 채택 → 왼쪽 파일이 오른쪽 내용을 가져야 한다
        state.set(changes[0], MergeDecision.RIGHT)
        left_result = state.apply_to_left(chunks)
        assert left_result == right

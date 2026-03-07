"""사이드-바이-사이드 diff 뷰 위젯 (가상 스크롤 포함)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from rich.console import Group
from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

from ..models.diff_engine import (
    AlignedLine,
    DiffChunk,
    build_aligned_lines,
    compute_diff,
    first_row_of_chunk,
    get_change_chunks,
)
from ..models.merge_state import MergeDecision, MergeState
from ..utils.file_utils import read_lines, write_lines

# ── Catppuccin Mocha 팔레트 ────────────────────────────────────────────────────
_C = {
    "bg":        "#1e1e2e",
    "surface":   "#313244",
    "overlay":   "#45475a",
    "subtext":   "#6c7086",
    "text":      "#cdd6f4",
    "red":       "#f38ba8",
    "green":     "#a6e3a1",
    "yellow":    "#f9e2af",
    "blue":      "#89b4fa",
    "teal":      "#94e2d5",
    "purple":    "#cba6f7",
    # diff 배경 (어두운 톤)
    "del_bg":    "#3d1515",
    "del_bg_hi": "#5c2020",
    "ins_bg":    "#153d15",
    "ins_bg_hi": "#206020",
    "rep_bg_l":  "#3d3415",
    "rep_bg_l_hi": "#5c5020",
    "rep_bg_r":  "#153d34",
    "rep_bg_r_hi": "#206050",
    "acc_bg":    "#1a3a1a",
    "acc_bg_r":  "#1a1a3a",
    "empty_bg":  "#252525",
    "gutter":    "#45475a",
}


class DiffViewWidget(Widget):
    """사이드-바이-사이드 diff 뷰어 (머지 기능 포함)."""

    can_focus = True

    # ── 반응형 상태 ──────────────────────────────────────────────────────────
    current_change_idx: reactive[int] = reactive(0)  # change_chunks 내 인덱스
    scroll_offset: reactive[int] = reactive(0)

    # ── 메시지 ───────────────────────────────────────────────────────────────
    class StateChanged(Message):
        """diff 상태가 변경될 때 발행."""

        def __init__(
            self,
            total_changes: int,
            current_change: int,
            is_modified: bool,
            left_path: Optional[Path],
            right_path: Optional[Path],
        ) -> None:
            super().__init__()
            self.total_changes = total_changes
            self.current_change = current_change
            self.is_modified = is_modified
            self.left_path = left_path
            self.right_path = right_path

    class SaveResult(Message):
        """저장 결과 알림."""

        def __init__(self, success: bool, message: str) -> None:
            super().__init__()
            self.success = success
            self.message = message

    class LoadError(Message):
        """파일 로드 실패 알림."""

        def __init__(self, message: str) -> None:
            super().__init__()
            self.message = message

    # ── 초기화 ───────────────────────────────────────────────────────────────
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._left_path: Optional[Path] = None
        self._right_path: Optional[Path] = None
        self._left_lines: List[str] = []
        self._right_lines: List[str] = []
        self._chunks: List[DiffChunk] = []
        self._aligned: List[AlignedLine] = []
        self._change_chunks: List[int] = []  # 변경된 청크 인덱스 목록
        self._merge_state: MergeState = MergeState(0)
        self._error_msg: Optional[str] = None

    # ── 공개 API ─────────────────────────────────────────────────────────────
    def load(self, left_path: Optional[Path], right_path: Optional[Path]) -> None:
        """두 파일을 로드하고 diff를 계산한다."""
        self._left_path = left_path
        self._right_path = right_path
        self._error_msg = None

        left_lines, l_err = self._safe_read(left_path)
        right_lines, r_err = self._safe_read(right_path)

        if l_err and left_path:
            self._error_msg = f"왼쪽: {l_err}"
            self.post_message(self.LoadError(self._error_msg))
            return
        if r_err and right_path:
            self._error_msg = f"오른쪽: {r_err}"
            self.post_message(self.LoadError(self._error_msg))
            return

        self._left_lines = left_lines
        self._right_lines = right_lines
        self._chunks = compute_diff(left_lines, right_lines)
        self._aligned = build_aligned_lines(self._chunks)
        self._change_chunks = get_change_chunks(self._chunks)
        self._merge_state = MergeState(len(self._chunks))

        self.current_change_idx = 0
        self.scroll_offset = 0
        self._scroll_to_current()
        self._emit_state()
        self.refresh()

    def next_chunk(self) -> None:
        if not self._change_chunks:
            return
        self.current_change_idx = (self.current_change_idx + 1) % len(self._change_chunks)
        self._scroll_to_current()
        self._emit_state()
        self.refresh()

    def prev_chunk(self) -> None:
        if not self._change_chunks:
            return
        self.current_change_idx = (self.current_change_idx - 1) % len(self._change_chunks)
        self._scroll_to_current()
        self._emit_state()
        self.refresh()

    def accept_left(self) -> None:
        """현재 청크에서 왼쪽을 채택한다 (오른쪽 파일에 반영)."""
        if not self._change_chunks:
            return
        chunk_idx = self._change_chunks[self.current_change_idx]
        self._merge_state.set(chunk_idx, MergeDecision.LEFT)
        self._emit_state()
        self.refresh()

    def accept_right(self) -> None:
        """현재 청크에서 오른쪽을 채택한다 (왼쪽 파일에 반영)."""
        if not self._change_chunks:
            return
        chunk_idx = self._change_chunks[self.current_change_idx]
        self._merge_state.set(chunk_idx, MergeDecision.RIGHT)
        self._emit_state()
        self.refresh()

    def accept_all_left(self) -> None:
        """모든 변경 청크에서 왼쪽을 채택한다."""
        self._merge_state.accept_all_left(self._change_chunks)
        self._emit_state()
        self.refresh()

    def accept_all_right(self) -> None:
        """모든 변경 청크에서 오른쪽을 채택한다."""
        self._merge_state.accept_all_right(self._change_chunks)
        self._emit_state()
        self.refresh()

    def revert_current(self) -> None:
        """현재 청크 결정을 취소한다."""
        if not self._change_chunks:
            return
        chunk_idx = self._change_chunks[self.current_change_idx]
        self._merge_state.set(chunk_idx, MergeDecision.NONE)
        self._emit_state()
        self.refresh()

    def save(self) -> None:
        """머지 결정에 따라 수정된 파일을 저장한다."""
        saved = []
        errors = []

        if self._merge_state.is_right_modified() and self._right_path:
            lines = self._merge_state.apply_to_right(self._chunks)
            err = write_lines(self._right_path, lines)
            if err:
                errors.append(f"오른쪽 저장 실패: {err}")
            else:
                saved.append(str(self._right_path))
                # 저장 후 diff 재계산
                self._right_lines = lines
                self._rechunk()

        if self._merge_state.is_left_modified() and self._left_path:
            lines = self._merge_state.apply_to_left(self._chunks)
            err = write_lines(self._left_path, lines)
            if err:
                errors.append(f"왼쪽 저장 실패: {err}")
            else:
                saved.append(str(self._left_path))
                self._left_lines = lines
                self._rechunk()

        if errors:
            self.post_message(self.SaveResult(False, "\n".join(errors)))
        elif saved:
            self.post_message(self.SaveResult(True, f"저장됨: {', '.join(saved)}"))
        else:
            self.post_message(self.SaveResult(False, "저장할 변경사항이 없습니다"))

    # ── 스크롤 ───────────────────────────────────────────────────────────────
    def scroll_up(self, amount: int = 1) -> None:
        self.scroll_offset = max(0, self.scroll_offset - amount)
        self.refresh()

    def scroll_down(self, amount: int = 1) -> None:
        max_offset = max(0, len(self._aligned) - self.size.height)
        self.scroll_offset = min(max_offset, self.scroll_offset + amount)
        self.refresh()

    # ── 렌더링 ───────────────────────────────────────────────────────────────
    def render(self):
        if self._error_msg:
            return Text(f"  오류: {self._error_msg}", style=Style(color=_C["red"]))

        if not self._aligned:
            return Text("  (동일한 파일)", style=Style(color=_C["subtext"]))

        h = self.size.height
        w = self.size.width
        if w < 30 or h < 3:
            return Text("너무 좁음")

        # 레이아웃 계산: [gutter][content]│[gutter][content]
        gutter_w = 6   # " 1234│ " → 6 chars
        sep_w = 1      # "│"
        content_w = max(1, (w - 2 * gutter_w - sep_w) // 2)

        current_chunk_idx = (
            self._change_chunks[self.current_change_idx]
            if self._change_chunks and 0 <= self.current_change_idx < len(self._change_chunks)
            else -1
        )

        visible = self._aligned[self.scroll_offset: self.scroll_offset + h]
        rows: List[Text] = []

        for row in visible:
            is_current = (row.chunk_idx == current_chunk_idx and row.tag != "equal")
            decision = self._merge_state.get(row.chunk_idx)
            l_style, r_style = self._styles(row.tag, is_current, decision)

            left_no = f"{row.left_lineno:>4}" if row.left_lineno is not None else "    "
            right_no = f"{row.right_lineno:>4}" if row.right_lineno is not None else "    "

            left_text = _clip(row.left_text, content_w)
            right_text = _clip(row.right_text, content_w)

            # 머지 결정 인디케이터
            l_indicator, r_indicator = self._decision_indicator(row.tag, decision)

            line = Text(no_wrap=True, overflow="crop")
            line.append(f"{left_no}│", style=Style(color=_C["gutter"]))
            line.append(l_indicator, style=Style(color=_C["purple"], bold=True))
            line.append(left_text.ljust(content_w), style=l_style)
            line.append("│", style=Style(color=_C["gutter"]))
            line.append(f"{right_no}│", style=Style(color=_C["gutter"]))
            line.append(r_indicator, style=Style(color=_C["purple"], bold=True))
            line.append(right_text.ljust(content_w), style=r_style)
            rows.append(line)

        # 빈 행으로 패딩
        blank = Text(" " * w)
        while len(rows) < h:
            rows.append(blank)

        return Group(*rows)

    # ── 내부 헬퍼 ────────────────────────────────────────────────────────────
    def _safe_read(self, path: Optional[Path]):
        if path is None:
            return [], None
        return read_lines(path)

    def _rechunk(self) -> None:
        self._chunks = compute_diff(self._left_lines, self._right_lines)
        self._aligned = build_aligned_lines(self._chunks)
        self._change_chunks = get_change_chunks(self._chunks)
        self._merge_state = MergeState(len(self._chunks))
        self.current_change_idx = 0
        self._scroll_to_current()
        self._emit_state()
        self.refresh()

    def _scroll_to_current(self) -> None:
        if not self._change_chunks:
            return
        chunk_idx = self._change_chunks[self.current_change_idx]
        row = first_row_of_chunk(self._aligned, chunk_idx)
        h = self.size.height or 20
        # 현재 청크가 뷰의 가운데에 오도록
        self.scroll_offset = max(0, row - h // 3)

    def _emit_state(self) -> None:
        self.post_message(
            self.StateChanged(
                total_changes=len(self._change_chunks),
                current_change=self.current_change_idx + 1 if self._change_chunks else 0,
                is_modified=self._merge_state.has_any_decision(),
                left_path=self._left_path,
                right_path=self._right_path,
            )
        )

    @staticmethod
    def _styles(
        tag: str, is_current: bool, decision: MergeDecision
    ) -> tuple[Style, Style]:
        """태그·현재 여부·결정에 따른 (왼쪽, 오른쪽) 스타일을 반환한다."""
        if tag == "equal":
            s = Style(color=_C["text"])
            return s, s

        # 결정이 내려진 경우
        if decision == MergeDecision.LEFT:
            return (
                Style(color=_C["green"], bgcolor=_C["acc_bg"]),
                Style(color=_C["green"], bgcolor=_C["acc_bg"]),
            )
        if decision == MergeDecision.RIGHT:
            return (
                Style(color=_C["blue"], bgcolor=_C["acc_bg_r"]),
                Style(color=_C["blue"], bgcolor=_C["acc_bg_r"]),
            )

        # 결정 전: 태그에 따라 색상 지정
        if tag == "delete":
            bg = _C["del_bg_hi"] if is_current else _C["del_bg"]
            return (
                Style(color=_C["red"], bgcolor=bg),
                Style(color=_C["subtext"], bgcolor=_C["empty_bg"]),
            )
        if tag == "insert":
            bg = _C["ins_bg_hi"] if is_current else _C["ins_bg"]
            return (
                Style(color=_C["subtext"], bgcolor=_C["empty_bg"]),
                Style(color=_C["green"], bgcolor=bg),
            )
        if tag == "replace":
            l_bg = _C["rep_bg_l_hi"] if is_current else _C["rep_bg_l"]
            r_bg = _C["rep_bg_r_hi"] if is_current else _C["rep_bg_r"]
            return (
                Style(color=_C["yellow"], bgcolor=l_bg),
                Style(color=_C["teal"], bgcolor=r_bg),
            )

        return Style(), Style()

    @staticmethod
    def _decision_indicator(tag: str, decision: MergeDecision) -> tuple[str, str]:
        """머지 결정 방향 인디케이터 문자를 반환한다."""
        if tag == "equal":
            return " ", " "
        if decision == MergeDecision.LEFT:
            return "✓", "✓"
        if decision == MergeDecision.RIGHT:
            return "✓", "✓"
        return " ", " "


def _clip(text: str, width: int) -> str:
    """텍스트를 지정 너비로 잘라낸다 (탭 처리 포함)."""
    text = text.replace("\t", "    ")
    return text[:width] if len(text) > width else text

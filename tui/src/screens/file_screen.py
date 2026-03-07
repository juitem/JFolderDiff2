"""파일 diff / 머지 화면."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Footer, Label, Static

from ..models.folder_diff import FolderEntry
from ..widgets.diff_view_widget import DiffViewWidget


class FileInfoBar(Static):
    """파일 이름, diff 위치, 수정 상태를 표시하는 상단 바."""

    def __init__(self, entry: FolderEntry) -> None:
        super().__init__()
        self._entry = entry
        self._total = 0
        self._current = 0
        self._modified = False

    def update_state(self, total: int, current: int, modified: bool) -> None:
        self._total = total
        self._current = current
        self._modified = modified
        self.refresh()

    def render(self):
        from rich.columns import Columns
        from rich.panel import Panel

        # 파일명
        name = Text(f"📄 {self._entry.name}", style="bold #cba6f7")

        # diff 위치
        if self._total > 0:
            diff_info = Text(
                f"  [{self._current}/{self._total} diff]",
                style="#f9e2af",
            )
        else:
            diff_info = Text("  [동일한 파일]", style="#6c7086")

        # 수정 상태
        if self._modified:
            mod_info = Text("  [미저장 변경 있음]", style="bold #f38ba8")
        else:
            mod_info = Text("", style="")

        content = Text.assemble(name, diff_info, mod_info)

        # 경로 표시
        left_str = str(self._entry.left_abs or "(없음)")
        right_str = str(self._entry.right_abs or "(없음)")
        path_info = Text(
            f"  {left_str}  ←→  {right_str}",
            style="#6c7086",
            overflow="ellipsis",
            no_wrap=True,
        )

        from rich.console import Group as RichGroup
        return RichGroup(content, path_info)


class FileScreen(Screen):
    """파일 diff 및 머지 화면."""

    BINDINGS = [
        Binding("b,escape", "back", "뒤로", show=True),
        Binding("n,tab", "next_chunk", "다음 diff", show=True),
        Binding("p,shift+tab", "prev_chunk", "이전 diff", show=True),
        Binding("right,l", "accept_left", "왼쪽 채택 →", show=True),
        Binding("left,h", "accept_right", "오른쪽 채택 ←", show=True),
        Binding("ctrl+right", "accept_all_left", "전체 왼쪽 채택", show=False),
        Binding("ctrl+left", "accept_all_right", "전체 오른쪽 채택", show=False),
        Binding("u", "revert", "현재 취소", show=True),
        Binding("s,ctrl+s", "save", "저장", show=True),
        Binding("up,k", "scroll_up", "스크롤 ↑", show=False),
        Binding("down,j", "scroll_down", "스크롤 ↓", show=False),
        Binding("pageup", "page_up", "페이지 ↑", show=False),
        Binding("pagedown", "page_down", "페이지 ↓", show=False),
    ]

    CSS = """
    FileScreen {
        background: #1e1e2e;
    }

    #file-info {
        height: 2;
        background: #313244;
        padding: 0 1;
        dock: top;
    }

    DiffViewWidget {
        height: 1fr;
        background: #1e1e2e;
    }

    DiffViewWidget:focus {
        border: none;
    }

    #notify-bar {
        height: 1;
        background: #313244;
        color: #a6adc8;
        content-align: center middle;
        dock: bottom;
        padding: 0 1;
    }
    """

    def __init__(self, entry: FolderEntry) -> None:
        super().__init__()
        self._entry = entry
        self._info_bar: Optional[FileInfoBar] = None
        self._notify_text = ""

    def compose(self) -> ComposeResult:
        self._info_bar = FileInfoBar(self._entry)
        yield self._info_bar
        yield DiffViewWidget(id="diff-view")
        yield Label("", id="notify-bar")
        yield Footer()

    def on_mount(self) -> None:
        diff_view = self.query_one("#diff-view", DiffViewWidget)
        diff_view.load(self._entry.left_abs, self._entry.right_abs)
        diff_view.focus()

    # ── 메시지 핸들러 ─────────────────────────────────────────────────────────
    def on_diff_view_widget_state_changed(self, msg: DiffViewWidget.StateChanged) -> None:
        if self._info_bar:
            self._info_bar.update_state(msg.total_changes, msg.current_change, msg.is_modified)

    def on_diff_view_widget_save_result(self, msg: DiffViewWidget.SaveResult) -> None:
        if msg.success:
            self._notify(f"✓ {msg.message}", style="green")
        else:
            self._notify(f"✗ {msg.message}", style="red")

    def on_diff_view_widget_load_error(self, msg: DiffViewWidget.LoadError) -> None:
        self._notify(f"✗ {msg.message}", style="red")

    # ── 액션 ─────────────────────────────────────────────────────────────────
    def action_back(self) -> None:
        self.app.pop_screen()

    def action_next_chunk(self) -> None:
        self.query_one("#diff-view", DiffViewWidget).next_chunk()

    def action_prev_chunk(self) -> None:
        self.query_one("#diff-view", DiffViewWidget).prev_chunk()

    def action_accept_left(self) -> None:
        """현재 청크에서 왼쪽을 채택한다 (오른쪽 파일에 반영)."""
        self.query_one("#diff-view", DiffViewWidget).accept_left()
        self._notify("→ 왼쪽 채택 (오른쪽 파일에 반영 예정)", style="yellow")

    def action_accept_right(self) -> None:
        """현재 청크에서 오른쪽을 채택한다 (왼쪽 파일에 반영)."""
        self.query_one("#diff-view", DiffViewWidget).accept_right()
        self._notify("← 오른쪽 채택 (왼쪽 파일에 반영 예정)", style="yellow")

    def action_accept_all_left(self) -> None:
        self.query_one("#diff-view", DiffViewWidget).accept_all_left()
        self._notify("→ 모든 청크: 왼쪽 채택", style="yellow")

    def action_accept_all_right(self) -> None:
        self.query_one("#diff-view", DiffViewWidget).accept_all_right()
        self._notify("← 모든 청크: 오른쪽 채택", style="yellow")

    def action_revert(self) -> None:
        self.query_one("#diff-view", DiffViewWidget).revert_current()
        self._notify("현재 결정 취소됨", style="dim")

    def action_save(self) -> None:
        self.query_one("#diff-view", DiffViewWidget).save()

    def action_scroll_up(self) -> None:
        self.query_one("#diff-view", DiffViewWidget).scroll_up(3)

    def action_scroll_down(self) -> None:
        self.query_one("#diff-view", DiffViewWidget).scroll_down(3)

    def action_page_up(self) -> None:
        h = self.query_one("#diff-view", DiffViewWidget).size.height
        self.query_one("#diff-view", DiffViewWidget).scroll_up(max(1, h - 2))

    def action_page_down(self) -> None:
        h = self.query_one("#diff-view", DiffViewWidget).size.height
        self.query_one("#diff-view", DiffViewWidget).scroll_down(max(1, h - 2))

    # ── 알림 ─────────────────────────────────────────────────────────────────
    def _notify(self, message: str, style: str = "default") -> None:
        color = {
            "green": "#a6e3a1",
            "red": "#f38ba8",
            "yellow": "#f9e2af",
            "dim": "#6c7086",
        }.get(style, "#cdd6f4")
        self.query_one("#notify-bar", Label).update(
            Text(message, style=f"#{color[1:]}" if color.startswith("#") else color)
        )

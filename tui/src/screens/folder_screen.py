"""폴더 비교 화면."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Static

from ..models.folder_diff import FolderEntry, compare_folders, flatten_entries

# 상태별 아이콘과 색상
_STATUS_ICON = {
    "same":       ("  =  ", "dim"),
    "different":  ("  ~  ", "yellow"),
    "left_only":  ("  ←  ", "blue"),
    "right_only": ("  →  ", "green"),
}

_STATUS_LABEL = {
    "same":       "동일",
    "different":  "수정됨",
    "left_only":  "왼쪽만",
    "right_only": "오른쪽만",
}


class PathHeader(Static):
    """양쪽 경로를 표시하는 헤더."""

    def __init__(self, left: Path, right: Path) -> None:
        super().__init__()
        self._left = left
        self._right = right

    def render(self):
        from rich.columns import Columns
        from rich.panel import Panel
        from rich.text import Text

        left_t = Text(str(self._left), style="bold #89b4fa", overflow="ellipsis")
        right_t = Text(str(self._right), style="bold #a6e3a1", overflow="ellipsis")
        return Columns(
            [
                Panel(left_t, title="왼쪽", border_style="#89b4fa", height=3),
                Panel(right_t, title="오른쪽", border_style="#a6e3a1", height=3),
            ],
            equal=True,
        )


class FolderScreen(Screen):
    """두 폴더를 비교하는 메인 화면."""

    BINDINGS = [
        Binding("enter", "open_file", "열기", show=True),
        Binding("space", "toggle_dir", "펼치기/접기", show=True),
        Binding("r", "refresh", "새로고침", show=True),
        Binding("tab", "next_diff", "다음 diff", show=True),
        Binding("q", "quit", "종료", show=True),
        Binding("f", "filter_diff", "diff만 보기", show=False),
    ]

    CSS = """
    FolderScreen {
        background: #1e1e2e;
    }

    PathHeader {
        height: 3;
        dock: top;
    }

    #stats-bar {
        height: 1;
        background: #313244;
        color: #a6adc8;
        content-align: center middle;
        dock: top;
    }

    #file-table {
        background: #1e1e2e;
        height: 1fr;
    }

    #file-table > .datatable--header {
        background: #313244;
        color: #cba6f7;
        text-style: bold;
    }

    #file-table > .datatable--cursor {
        background: #45475a;
        color: #cdd6f4;
    }

    #file-table > .datatable--odd-row {
        background: #1e1e2e;
    }

    #file-table > .datatable--even-row {
        background: #181825;
    }

    #no-result {
        background: #1e1e2e;
        color: #6c7086;
        content-align: center middle;
        height: 1fr;
    }
    """

    def __init__(self, left_path: Path, right_path: Path) -> None:
        super().__init__()
        self.left_path = left_path
        self.right_path = right_path
        self._entries: List[FolderEntry] = []
        self._flat: List[FolderEntry] = []
        self._expanded: set[str] = set()
        self._filter_diff_only = False

    def compose(self) -> ComposeResult:
        yield PathHeader(self.left_path, self.right_path)
        yield Label("  로딩 중…", id="stats-bar")
        table = DataTable(id="file-table", cursor_type="row", zebra_stripes=True)
        table.add_column("상태", width=7)
        table.add_column("이름", width=40)
        table.add_column("종류", width=8)
        yield table
        yield Footer()

    def on_mount(self) -> None:
        self._load_entries()

    # ── 데이터 로드 ──────────────────────────────────────────────────────────
    @work(thread=True)
    def _load_entries(self) -> None:
        entries = compare_folders(self.left_path, self.right_path)
        self.app.call_from_thread(self._populate, entries)

    def _populate(self, entries: List[FolderEntry]) -> None:
        self._entries = entries
        # 초기에는 모든 폴더 펼침
        self._expanded = {e.rel_path for e in flatten_entries(entries) if e.is_dir}
        self._refresh_table()

    def _refresh_table(self) -> None:
        table = self.query_one("#file-table", DataTable)
        table.clear()

        self._flat = flatten_entries(self._entries, self._expanded)
        if self._filter_diff_only:
            self._flat = [e for e in self._flat if e.status != "same"]

        for entry in self._flat:
            icon, color = _STATUS_ICON.get(entry.status, ("  ?  ", "white"))
            status_text = Text(icon, style=color)

            indent = "  " * entry.depth
            prefix = "📁 " if entry.is_dir else "📄 "
            name_str = indent + prefix + entry.name
            if entry.is_dir:
                arrow = " ▾" if entry.rel_path in self._expanded else " ▸"
                name_str += arrow
            name_text = Text(name_str, overflow="ellipsis")
            if entry.status == "same":
                name_text.stylize("dim")
            elif entry.status == "left_only":
                name_text.stylize("bold #89b4fa")
            elif entry.status == "right_only":
                name_text.stylize("bold #a6e3a1")
            elif entry.status == "different":
                name_text.stylize("bold #f9e2af")

            kind_text = Text("폴더" if entry.is_dir else "파일", style="dim")
            table.add_row(status_text, name_text, kind_text)

        # 통계 업데이트
        self._update_stats()

    def _update_stats(self) -> None:
        total = len(self._flat)
        same = sum(1 for e in self._flat if e.status == "same" and not e.is_dir)
        diff = sum(1 for e in self._flat if e.status == "different")
        l_only = sum(1 for e in self._flat if e.status == "left_only" and not e.is_dir)
        r_only = sum(1 for e in self._flat if e.status == "right_only" and not e.is_dir)

        stats = (
            f"  총 {total}개  │  "
            f"[dim]동일 {same}[/]  │  "
            f"[yellow]수정 {diff}[/]  │  "
            f"[blue]왼쪽만 {l_only}[/]  │  "
            f"[green]오른쪽만 {r_only}[/]"
            f"{'  │  [purple][diff만 표시][/]' if self._filter_diff_only else ''}"
        )
        self.query_one("#stats-bar", Label).update(stats)

    # ── 액션 ─────────────────────────────────────────────────────────────────
    def action_open_file(self) -> None:
        entry = self._current_entry()
        if entry is None:
            return
        if entry.is_dir:
            self.action_toggle_dir()
            return
        from .file_screen import FileScreen  # 순환 import 방지
        self.app.push_screen(FileScreen(entry))

    def action_toggle_dir(self) -> None:
        entry = self._current_entry()
        if entry is None or not entry.is_dir:
            return
        if entry.rel_path in self._expanded:
            self._expanded.discard(entry.rel_path)
        else:
            self._expanded.add(entry.rel_path)
        self._refresh_table()

    def action_refresh(self) -> None:
        self._load_entries()

    def action_next_diff(self) -> None:
        """diff 상태인 다음 항목으로 이동한다."""
        table = self.query_one("#file-table", DataTable)
        cursor = table.cursor_row
        for i in range(cursor + 1, len(self._flat)):
            if self._flat[i].status != "same":
                table.move_cursor(row=i)
                return

    def action_filter_diff(self) -> None:
        self._filter_diff_only = not self._filter_diff_only
        self._refresh_table()

    def action_quit(self) -> None:
        self.app.exit()

    def _current_entry(self) -> Optional[FolderEntry]:
        table = self.query_one("#file-table", DataTable)
        row = table.cursor_row
        if 0 <= row < len(self._flat):
            return self._flat[row]
        return None

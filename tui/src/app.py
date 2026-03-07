"""FolderDiff 메인 Textual 앱."""
from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Label

from .screens.folder_screen import FolderScreen


class FolderDiffApp(App):
    """Meld 스타일 폴더/파일 diff 및 머지 도구."""

    TITLE = "FolderDiff"
    SUB_TITLE = "폴더 비교 및 머지 도구"
    CSS = """
    App {
        background: #1e1e2e;
        color: #cdd6f4;
    }
    """

    def __init__(self, left_path: Path, right_path: Path) -> None:
        super().__init__()
        self.left_path = left_path
        self.right_path = right_path

    def on_mount(self) -> None:
        self.push_screen(FolderScreen(self.left_path, self.right_path))

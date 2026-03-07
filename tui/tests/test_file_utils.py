"""file_utils 모듈 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.utils.file_utils import is_binary, read_lines, write_lines


class TestIsBinary:
    def test_text_file_is_not_binary(self, tmp_path: Path):
        f = tmp_path / "text.txt"
        f.write_text("Hello\nWorld\n")
        assert is_binary(f) is False

    def test_binary_file_with_null_byte(self, tmp_path: Path):
        f = tmp_path / "binary.bin"
        f.write_bytes(b"PNG\x00\x01\x02")
        assert is_binary(f) is True

    def test_nonexistent_file_treated_as_binary(self, tmp_path: Path):
        assert is_binary(tmp_path / "nonexistent.txt") is True

    def test_empty_file_is_not_binary(self, tmp_path: Path):
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        assert is_binary(f) is False


class TestReadLines:
    def test_reads_utf8_text_file(self, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_text("line1\nline2\nline3\n", encoding="utf-8")
        lines, err = read_lines(f)
        assert err is None
        assert len(lines) == 3
        assert lines[0] == "line1\n"

    def test_returns_error_for_nonexistent_file(self, tmp_path: Path):
        lines, err = read_lines(tmp_path / "missing.txt")
        assert lines == []
        assert err is not None

    def test_returns_error_for_binary_file(self, tmp_path: Path):
        f = tmp_path / "binary.bin"
        f.write_bytes(b"PNG\x00\x01\x02")
        lines, err = read_lines(f)
        assert lines == []
        assert err is not None

    def test_returns_error_for_none_path(self):
        lines, err = read_lines(None)
        assert lines == []
        assert err is not None

    def test_reads_file_with_no_trailing_newline(self, tmp_path: Path):
        f = tmp_path / "file.txt"
        f.write_text("line1\nline2", encoding="utf-8")
        lines, err = read_lines(f)
        assert err is None
        assert len(lines) == 2

    def test_reads_latin1_encoded_file(self, tmp_path: Path):
        f = tmp_path / "latin1.txt"
        f.write_bytes("Ä Ö Ü\n".encode("latin-1"))
        lines, err = read_lines(f)
        assert err is None
        assert len(lines) == 1


class TestWriteLines:
    def test_writes_lines_to_file(self, tmp_path: Path):
        f = tmp_path / "output.txt"
        lines = ["line1\n", "line2\n", "line3\n"]
        err = write_lines(f, lines)
        assert err is None
        assert f.read_text(encoding="utf-8") == "line1\nline2\nline3\n"

    def test_overwrites_existing_file(self, tmp_path: Path):
        f = tmp_path / "output.txt"
        f.write_text("old content")
        err = write_lines(f, ["new content\n"])
        assert err is None
        assert f.read_text() == "new content\n"

    def test_returns_error_for_unwritable_path(self, tmp_path: Path):
        bad_path = tmp_path / "nonexistent_dir" / "file.txt"
        err = write_lines(bad_path, ["content\n"])
        assert err is not None

    def test_roundtrip_read_write(self, tmp_path: Path):
        f = tmp_path / "roundtrip.txt"
        original = ["hello\n", "world\n"]
        write_lines(f, original)
        lines, err = read_lines(f)
        assert err is None
        assert lines == original

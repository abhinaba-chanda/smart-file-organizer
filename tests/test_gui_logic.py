"""Tests for the desktop window's logic (no display needed) plus a window smoke test when a display exists."""

import os
from pathlib import Path

import pytest

from smart_organizer import __version__
from smart_organizer import gui_logic as logic
from smart_organizer.config import ConfigError


def test_footer_and_title():
    assert logic.FOOTER == f"{__version__} \u00b7 Abhinaba-Dev"
    assert __version__ == "V1"
    assert logic.APP_TITLE == "Smart File Organizer"


def test_mode_labels_cover_cli_modes():
    from smart_organizer.config import MODES

    assert list(logic.MODE_LABELS) == list(MODES)


def test_folder_from_argv(tmp_path: Path):
    assert logic.folder_from_argv([str(tmp_path)]) == tmp_path.resolve()
    assert logic.folder_from_argv([f'"{tmp_path}"']) == tmp_path.resolve()
    assert logic.folder_from_argv(["--flag", str(tmp_path / "nope")]) is None


def test_default_folder_prefers_downloads(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert logic.default_folder() == tmp_path
    (tmp_path / "Downloads").mkdir()
    assert logic.default_folder() == tmp_path / "Downloads"


def test_preview_rows_and_summary(messy: Path):
    moves = logic.make_plan(messy, "type")
    rows = logic.preview_rows(moves, messy)
    assert ("song.mp3", "Music") in rows
    assert all(not name.startswith(".") for name, _ in rows)
    summary = logic.plan_summary(moves)
    assert summary.startswith(f"{len(moves)} files \u2192 ")
    assert logic.plan_summary([]) == "All tidy. Nothing to move here."


def test_date_mode_destination(messy: Path):
    rows = dict(logic.preview_rows(logic.make_plan(messy, "date"), messy))
    assert rows["song.mp3"] == "2025/03"


def test_unknown_mode_rejected(messy: Path):
    with pytest.raises(ValueError):
        logic.make_plan(messy, "size")


def test_organize_then_undo(messy: Path):
    assert not logic.can_undo(messy)
    moves = logic.make_plan(messy, "type")
    seen = []
    result = logic.organize(moves, messy, on_progress=seen.append)
    assert len(seen) == len(moves) == len(result.done)
    assert logic.run_summary(result) == f"Organized {len(moves)} files"
    assert not (messy / "song.mp3").exists()
    assert logic.can_undo(messy)
    back = logic.undo_last(messy)
    assert logic.run_summary(back, "Put back") == f"Put back {len(moves)} files"
    assert (messy / "song.mp3").exists()
    assert not logic.can_undo(messy)


def test_duplicate_rows(messy: Path):
    rows, text = logic.duplicate_rows(messy)
    assert rows == [("report copy.pdf", "copy of report.pdf")] or rows == [("report.pdf", "copy of report copy.pdf")]
    assert text.startswith("1 extra copy")


def test_no_duplicates(tmp_path: Path):
    (tmp_path / "a.txt").write_text("a")
    assert logic.duplicate_rows(tmp_path) == ([], "No duplicates found.")


def test_friendly_errors():
    assert "nothing to undo" in logic.friendly_error(FileNotFoundError("No undo log found in x"))
    assert "organizer.yaml" in logic.friendly_error(ConfigError("bad"))
    assert "didn't allow" in logic.friendly_error(PermissionError(13, "denied", "C:/x/file.txt"))
    assert "isn't a folder" in logic.friendly_error(NotADirectoryError("x"))
    assert logic.friendly_error(RuntimeError("boom")) == "Something went wrong: boom"


def test_dark_mode_override(monkeypatch):
    monkeypatch.setenv("SFO_THEME", "dark")
    assert logic.system_prefers_dark() is True
    monkeypatch.setenv("SFO_THEME", "light")
    assert logic.system_prefers_dark() is False


def test_self_test(tmp_path: Path):
    report = logic.self_test(tmp_path / "st")
    assert report.ok, report.lines
    assert report.lines[-1] == "ok"


def test_gui_logic_does_not_import_tkinter_or_rich():
    import subprocess
    import sys

    code = ("import sys, smart_organizer.gui_logic; "
            "print(any(m.split('.')[0] in ('tkinter', 'rich') for m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
    assert out == "False"


def _display_available() -> bool:
    try:
        import tkinter

        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _display_available(), reason="no display (headless)")
def test_window_builds_and_previews(messy: Path):
    import tkinter

    from smart_organizer.gui import App

    root = tkinter.Tk()
    root.withdraw()
    try:
        app = App(root, folder=messy, auto_preview=False)
        assert root.title() == "Smart File Organizer"
        app._on_preview((messy, logic.make_plan(messy, "type")))
        assert len(app.tree.get_children()) == len(app.moves) > 0
        assert str(app.organize_btn.cget("state")) == "normal"
        assert str(app.undo_btn.cget("state")) == "disabled"
    finally:
        root.destroy()

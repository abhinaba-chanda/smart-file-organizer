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


def test_byline_and_github_link():
    assert logic.AUTHOR == "Abhinaba-Dev"
    assert logic.BYLINE == "by Abhinaba-Dev"
    assert logic.GITHUB_URL == "https://github.com/abhinaba-chanda"


def test_settings_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SFO_SETTINGS_DIR", str(tmp_path / "cfg"))
    first = logic.load_settings()  # nothing saved yet -> defaults
    assert first["mode"] == "type" and first["recursive"] is False
    assert logic.save_settings(str(tmp_path), "date", True)
    assert logic.load_settings() == {"folder": str(tmp_path), "mode": "date", "recursive": True}


def test_settings_ignore_bad_values(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SFO_SETTINGS_DIR", str(tmp_path))
    (tmp_path / "settings.json").write_text('{"folder": "/no/such/folder", "mode": "nope", "recursive": "x"}')
    s = logic.load_settings()
    assert s["mode"] == "type" and s["recursive"] is False and Path(s["folder"]).is_dir()
    (tmp_path / "settings.json").write_text("not json")
    assert logic.load_settings()["mode"] == "type"


def test_windows_settings_location(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SFO_SETTINGS_DIR", raising=False)
    monkeypatch.setattr(logic.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert logic.settings_path() == tmp_path / "SmartFileOrganizer" / "settings.json"


def test_unticked_files_are_left_alone(messy: Path):
    moves = logic.make_plan(messy, "type")
    keep = next(i for i, m in enumerate(moves) if m.src.name == "song.mp3")
    chosen = logic.included(moves, {keep})
    assert len(chosen) == len(moves) - 1
    logic.organize(chosen, messy)
    assert (messy / "song.mp3").exists()
    assert not (messy / "photo.JPG").exists()


def test_subfolders(messy: Path):
    sub = messy / "old stuff"
    sub.mkdir()
    (sub / "clip.mp4").write_bytes(b"mp4")
    flat = {m.src.name for m in logic.make_plan(messy, "type")}
    deep = {m.src.name for m in logic.make_plan(messy, "type", recursive=True)}
    assert "clip.mp4" not in flat and "clip.mp4" in deep


def test_move_duplicates_aside_and_undo(messy: Path):
    moves = logic.duplicate_moves(messy)
    assert len(moves) == 1 and moves[0].dst.parent == messy.resolve() / "Duplicates"
    extra = moves[0].src.name
    logic.organize(moves, messy)
    assert (messy / "Duplicates" / extra).exists() and not (messy / extra).exists()
    assert (messy / "report.pdf").exists() or (messy / "report copy.pdf").exists()  # one copy always stays
    logic.undo_last(messy)
    assert (messy / extra).exists() and not (messy / "Duplicates").exists()
    assert logic.duplicate_summary([]) == "No duplicates found."


def test_open_in_explorer_uses_startfile_on_windows(monkeypatch, tmp_path: Path):
    opened = []
    monkeypatch.setattr(logic.sys, "platform", "win32")
    monkeypatch.setattr(logic.os, "startfile", opened.append, raising=False)
    logic.open_in_explorer(tmp_path)
    assert opened == [str(tmp_path)]


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
        # untick a file: it is left out of the run and the count says so
        app.toggle(0)
        assert len(app.included_moves()) == len(app.moves) - 1
        assert "1 skipped" in app.status.get()
        app.toggle(0)
        assert len(app.included_moves()) == len(app.moves)
    finally:
        root.destroy()


@pytest.mark.skipif(not _display_available(), reason="no display (headless)")
def test_title_row_byline_and_github_button(messy: Path, monkeypatch):
    import tkinter

    from smart_organizer import gui
    from smart_organizer.gui import App

    opened = []
    monkeypatch.setattr(gui.webbrowser, "open", opened.append)
    root = tkinter.Tk()
    root.withdraw()
    try:
        app = App(root, folder=messy, auto_preview=False)
        assert app.byline.cget("text") == "by Abhinaba-Dev"
        assert app.github_url == "https://github.com/abhinaba-chanda"
        assert app.github_btn.cget("text") == "GitHub"
        assert str(app.github_btn.cget("cursor")) == "hand2"
        app.github_btn.invoke()
        assert opened == ["https://github.com/abhinaba-chanda"]
    finally:
        root.destroy()


@pytest.mark.skipif(not _display_available(), reason="no display (headless)")
def test_duplicates_view_moves_extras(messy: Path):
    import tkinter

    from smart_organizer.gui import App

    root = tkinter.Tk()
    root.withdraw()
    try:
        app = App(root, folder=messy, auto_preview=False)
        app._on_dupes(logic.duplicate_moves(messy))
        assert app.view == "dupes" and len(app.tree.get_children()) == 1
        assert app.organize_btn.cget("text") == "Move extras to Duplicates"
        assert str(app.organize_btn.cget("state")) == "normal"
    finally:
        root.destroy()

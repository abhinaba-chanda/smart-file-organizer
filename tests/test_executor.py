import json
from pathlib import Path

import pytest

from smart_organizer.config import load_config
from smart_organizer.executor import apply_plan, from_log_path, list_logs, to_log_path, undo
from smart_organizer.planner import build_plan


def snapshot(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".organize" not in p.parts}


def test_run_then_undo_restores_everything(messy: Path):
    before = snapshot(messy)
    result = apply_plan(build_plan(messy, load_config()), messy)
    assert not result.failed and result.log_path and result.log_path.exists()
    after = snapshot(messy)
    assert "Music/song.mp3" in after and "song.mp3" not in after
    undo(messy)
    assert snapshot(messy) == before
    # Folders created by the run are cleaned up again.
    assert not (messy / "Music").exists()
    assert list_logs(messy) == []


def test_log_uses_portable_relative_paths(messy: Path):
    result = apply_plan(build_plan(messy, load_config()), messy)
    data = json.loads(result.log_path.read_text(encoding="utf-8"))
    for entry in data["moves"]:
        assert "\\" not in entry["src"] and "\\" not in entry["dst"]
        assert not Path(entry["dst"]).is_absolute()


def test_windows_log_paths_are_understood(tmp_path: Path):
    assert from_log_path("Images\\Screenshots\\a.png", tmp_path) == tmp_path / "Images" / "Screenshots" / "a.png"
    assert from_log_path("Images/a.png", tmp_path) == tmp_path / "Images" / "a.png"
    assert to_log_path(tmp_path / "x" / "y.txt", tmp_path) == "x/y.txt"


def test_undo_skips_missing_files(messy: Path):
    apply_plan(build_plan(messy, load_config()), messy)
    (messy / "Music" / "song.mp3").unlink()
    result = undo(messy)
    assert any("song.mp3" in str(p) for p, _ in result.failed)
    assert (messy / "photo.JPG").exists()


def test_undo_without_log(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        undo(tmp_path)


def test_two_runs_undo_newest_first(messy: Path):
    cfg = load_config()
    apply_plan(build_plan(messy, cfg), messy)
    (messy / "new.mp3").write_bytes(b"later")
    apply_plan(build_plan(messy, cfg), messy)
    assert len(list_logs(messy)) == 2
    undo(messy)
    assert (messy / "new.mp3").exists() and not (messy / "song.mp3").exists()
    undo(messy)
    assert (messy / "song.mp3").exists()

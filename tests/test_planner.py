from pathlib import Path

from smart_organizer.config import load_config
from smart_organizer.planner import build_plan, iter_files, summarize, unique_destination


def rel(moves, root):
    return {m.src.name: m.dst.relative_to(root.resolve()).as_posix() for m in moves}


def test_type_mode(messy: Path):
    moves = build_plan(messy, load_config())
    r = rel(moves, messy)
    assert r["photo.JPG"] == "Images/photo.JPG"
    assert r["Screenshot 2026-01-01.png"] == "Images/Screenshots/Screenshot 2026-01-01.png"
    assert r["song.mp3"] == "Music/song.mp3"
    assert r["weird.xyz"] == "Other/weird.xyz"
    assert r["my notes ünïcode.txt"] == "Documents/my notes ünïcode.txt"


def test_hidden_and_ignored_files_are_skipped(messy: Path):
    names = {p.name for p in iter_files(messy, load_config())}
    assert ".hidden" not in names and "desktop.ini" not in names


def test_date_and_type_date_modes(messy: Path):
    cfg = load_config()
    assert rel(build_plan(messy, cfg, mode="date"), messy)["song.mp3"] == "2025/03/song.mp3"
    assert rel(build_plan(messy, cfg, mode="type-date"), messy)["song.mp3"] == "Music/2025/03/song.mp3"


def test_preview_does_not_touch_files(messy: Path):
    before = sorted(p.name for p in messy.iterdir())
    build_plan(messy, load_config())
    assert sorted(p.name for p in messy.iterdir()) == before


def test_name_collision_gets_suffix(messy: Path):
    (messy / "Images").mkdir()
    (messy / "Images" / "photo.JPG").write_bytes(b"already here")
    r = rel(build_plan(messy, load_config()), messy)
    assert r["photo.JPG"] == "Images/photo (1).JPG"


def test_unique_destination_within_plan(tmp_path: Path):
    target = tmp_path / "a.txt"
    import os
    taken = {os.path.normcase(os.path.abspath(target))}
    assert unique_destination(target, taken).name == "a (1).txt"


def test_duplicates_move(messy: Path):
    cfg = load_config()
    cfg.duplicates = "move"
    moves = build_plan(messy, cfg)
    dup = [m for m in moves if m.category == "Duplicate"]
    assert len(dup) == 1
    assert dup[0].dst.parent.name == "Duplicates"
    assert dup[0].duplicate_of is not None


def test_dest_folder(messy: Path, tmp_path_factory):
    out = tmp_path_factory.mktemp("sorted")
    moves = build_plan(messy, load_config(), dest=out)
    assert all(out.resolve() in m.dst.parents for m in moves)


def test_recursive_skips_already_sorted_folders(messy: Path):
    (messy / "Images").mkdir()
    (messy / "Images" / "old.png").write_bytes(b"x")
    (messy / "stuff").mkdir()
    (messy / "stuff" / "deep.mp3").write_bytes(b"y")
    r = rel(build_plan(messy, load_config(), recursive=True), messy)
    assert "old.png" not in r
    assert r["deep.mp3"] == "Music/deep.mp3"


def test_already_in_place_is_not_moved(tmp_path: Path):
    (tmp_path / "Music").mkdir()
    (tmp_path / "Music" / "a.mp3").write_bytes(b"x")
    assert build_plan(tmp_path / "Music", load_config(), dest=tmp_path) == []


def test_summarize(messy: Path):
    stats = summarize(build_plan(messy, load_config()))
    assert stats["Documents"][0] == 3

"""Everything the desktop window needs that does not touch tkinter (so it can be tested headless).

The window (``gui.py``) only draws; planning, moving, undoing and duplicate finding all come from
the same core modules the ``organize`` command uses.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from . import __version__
from .config import MODES, ConfigError, find_config, load_config
from .duplicates import find_duplicates
from .executor import RunResult, apply_plan, list_logs, undo
from .planner import Move, build_plan, human_size, iter_files, unique_destination

APP_TITLE = "Smart File Organizer"
AUTHOR = "Abhinaba-Dev"
BYLINE = f"by {AUTHOR}"
GITHUB_URL = "https://github.com/abhinaba-chanda"
FOOTER = f"{__version__} \u00b7 {AUTHOR}"
MODE_LABELS = {"type": "By type", "date": "By date", "type-date": "Type + date"}
assert set(MODE_LABELS) == set(MODES)


def default_folder() -> Path:
    """The Downloads folder if there is one, else the home folder."""
    home = Path.home()
    downloads = home / "Downloads"
    return downloads if downloads.is_dir() else home


def folder_from_argv(argv: Iterable[str]) -> Optional[Path]:
    """A folder passed on the command line (e.g. a folder dropped onto the .exe icon)."""
    for arg in argv:
        if arg.startswith("-"):
            continue
        p = Path(arg.strip().strip('"')).expanduser()
        if p.is_dir():
            return p.resolve()
    return None


def config_for(folder: Path):
    """The folder's organizer.yaml if it has one, else the built-in rules."""
    return load_config(find_config(Path(folder)))


def make_plan(folder: Path, mode: str, recursive: bool = False):
    """``build_plan`` with the folder's own rules (``recursive`` also picks up files in subfolders)."""
    if mode not in MODES:
        raise ValueError(f"Unknown mode {mode!r}")
    return build_plan(Path(folder), config_for(folder), mode=mode, recursive=recursive)


def included(moves: list[Move], skipped: Iterable[int]) -> list[Move]:
    """The moves still ticked in the preview (``skipped`` holds the row numbers the user unticked)."""
    skip = set(skipped)
    return [m for i, m in enumerate(moves) if i not in skip]


# ---------- remembered settings (last folder, grouping, subfolders) ----------

def settings_path() -> Path:
    """``%APPDATA%\\SmartFileOrganizer\\settings.json`` on Windows (``SFO_SETTINGS_DIR`` overrides)."""
    base = os.environ.get("SFO_SETTINGS_DIR")
    if base:
        return Path(base) / "settings.json"
    if sys.platform == "win32" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "SmartFileOrganizer" / "settings.json"
    return Path.home() / ".config" / "smart-file-organizer" / "settings.json"


def load_settings() -> dict:
    """Last folder, mode and subfolder choice; anything missing or broken falls back to the defaults."""
    out = {"folder": str(default_folder()), "mode": "type", "recursive": False}
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return out
    if not isinstance(data, dict):
        return out
    folder = data.get("folder")
    if isinstance(folder, str) and Path(folder).is_dir():
        out["folder"] = folder
    if data.get("mode") in MODES:
        out["mode"] = data["mode"]
    if isinstance(data.get("recursive"), bool):
        out["recursive"] = data["recursive"]
    return out


def save_settings(folder: str, mode: str, recursive: bool) -> bool:
    """Remember the choices for next time. Never raises (returns False if it couldn't save)."""
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"folder": str(folder), "mode": mode, "recursive": bool(recursive)},
                                   indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def open_in_explorer(folder: Path) -> None:
    """Open a folder in Explorer (Finder / the file manager elsewhere)."""
    folder = str(Path(folder))
    if sys.platform == "win32":
        os.startfile(folder)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", folder])
    else:
        subprocess.Popen(["xdg-open", folder])


def destination_label(move: Move, root: Path) -> str:
    """Where a file goes, relative to the organized folder, e.g. ``Images/2026``."""
    try:
        rel = move.dst.parent.resolve().relative_to(Path(root).resolve())
        text = rel.as_posix()
    except ValueError:
        text = str(move.dst.parent)
    if move.renamed:
        text += f"  (as {move.dst.name})"
    return text or "."


def preview_rows(moves: list[Move], root: Path) -> list[tuple[str, str]]:
    """``(file name, goes to)`` pairs for the preview list."""
    return [(m.src.name, destination_label(m, root)) for m in moves]


def plan_summary(moves: list[Move]) -> str:
    """One line for the status bar."""
    if not moves:
        return "All tidy. Nothing to move here."
    folders = {m.dst.parent for m in moves}
    total = sum(m.size for m in moves)
    files = "file" if len(moves) == 1 else "files"
    dirs = "folder" if len(folders) == 1 else "folders"
    return f"{len(moves)} {files} \u2192 {len(folders)} {dirs} \u00b7 {human_size(total)}"


def run_summary(result: RunResult, verb: str = "Organized") -> str:
    """Toast text after organizing or undoing."""
    n = len(result.done)
    text = f"{verb} {n} file{'s' if n != 1 else ''}"
    if result.failed:
        text += f", {len(result.failed)} skipped"
    return text


def can_undo(folder: Path) -> bool:
    """True when the folder has an organize run that can be put back."""
    try:
        return bool(list_logs(Path(folder)))
    except OSError:
        return False


def organize(moves: list[Move], folder: Path, on_progress: Optional[Callable[[Move], None]] = None) -> RunResult:
    return apply_plan(moves, Path(folder), on_progress=on_progress)


def undo_last(folder: Path) -> RunResult:
    return undo(Path(folder))


def duplicate_moves(folder: Path, recursive: bool = False) -> list[Move]:
    """Moves that put every extra copy of an identical file into the Duplicates folder (keeps the first)."""
    folder = Path(folder).resolve()
    cfg = config_for(folder)
    target_dir = folder.joinpath(*[p for p in cfg.duplicates_folder.replace("\\", "/").split("/") if p])
    taken: set[str] = set()
    moves: list[Move] = []
    for group in find_duplicates(list(iter_files(folder, cfg, recursive))):
        for extra in group[1:]:
            dst = unique_destination(target_dir / extra.name, taken)
            taken.add(os.path.normcase(os.path.abspath(dst)))
            moves.append(Move(src=extra, dst=dst, category="Duplicate", size=extra.stat().st_size,
                              duplicate_of=group[0]))
    return moves


def duplicate_summary(moves: list[Move]) -> str:
    if not moves:
        return "No duplicates found."
    copies = "copy" if len(moves) == 1 else "copies"
    return f"{len(moves)} extra {copies} \u00b7 {human_size(sum(m.size for m in moves))} wasted"


def duplicate_view(moves: list[Move]) -> list[tuple[str, str]]:
    """``(extra copy, copy of)`` rows for the duplicates view."""
    return [(m.src.name, f"copy of {m.duplicate_of.name}" if m.duplicate_of else "") for m in moves]


def duplicate_rows(folder: Path, recursive: bool = False) -> tuple[list[tuple[str, str]], str]:
    """Rows ``(extra copy, copy of)`` and a summary line for the duplicates view."""
    moves = duplicate_moves(folder, recursive)
    return duplicate_view(moves), duplicate_summary(moves)


def friendly_error(exc: BaseException) -> str:
    """Plain words for the error dialog."""
    if isinstance(exc, ConfigError):
        return f"The organizer.yaml in this folder has a problem:\n{exc}"
    if isinstance(exc, PermissionError):
        name = getattr(exc, "filename", None)
        where = f" ({Path(name).name})" if name else ""
        return f"Windows didn't allow access{where}. Close any app using these files, or pick another folder."
    if isinstance(exc, FileNotFoundError):
        if "undo log" in str(exc).lower():
            return "There's nothing to undo in this folder yet."
        return "That folder or file isn't there any more. Pick the folder again."
    if isinstance(exc, NotADirectoryError):
        return "That isn't a folder. Pick a folder instead."
    if isinstance(exc, OSError):
        return f"Something went wrong with a file: {exc.strerror or exc}"
    return f"Something went wrong: {exc}"


def system_prefers_dark() -> bool:
    """Windows 10/11 'Choose your app mode: Dark' setting (False anywhere else)."""
    if os.environ.get("SFO_THEME") in ("dark", "light"):
        return os.environ["SFO_THEME"] == "dark"
    if sys.platform != "win32":
        return False
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except OSError:
        return False


def resource_path(name: str) -> Optional[Path]:
    """A bundled file (next to the .exe's unpacked files) or the repo's packaging/ copy."""
    candidates = []
    if getattr(sys, "_MEIPASS", None):
        candidates.append(Path(sys._MEIPASS) / name)  # type: ignore[attr-defined]
    candidates.append(Path(__file__).resolve().parents[2] / "packaging" / name)
    for c in candidates:
        if c.is_file():
            return c
    return None


@dataclass
class SelfTestReport:
    ok: bool
    lines: list[str]


def self_test(workdir: Path) -> SelfTestReport:
    """Used by the release workflow on the built .exe: plan, organize and undo a tiny folder."""
    lines = [f"{APP_TITLE} {__version__}"]
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    for name, data in {"song.mp3": b"mp3" * 9, "photo.jpg": b"jpg", "notes.txt": b"hi", "notes copy.txt": b"hi"}.items():
        (workdir / name).write_bytes(data)
    moves = make_plan(workdir, "type")
    lines.append(plan_summary(moves))
    result = organize(moves, workdir)
    lines.append(run_summary(result))
    ok = not (workdir / "song.mp3").exists() and can_undo(workdir)
    dup_rows, dup_text = duplicate_rows(workdir / "Documents") if (workdir / "Documents").is_dir() else ([], "")
    lines.append(dup_text)
    back = undo_last(workdir)
    lines.append(run_summary(back, "Put back"))
    ok = ok and (workdir / "song.mp3").exists() and len(dup_rows) == 1
    dup_moves = duplicate_moves(workdir)
    moved = organize(dup_moves, workdir)
    lines.append(run_summary(moved, "Moved") + " to Duplicates")
    ok = ok and len(dup_moves) == 1 and (workdir / "Duplicates").is_dir()
    lines.append(run_summary(undo_last(workdir), "Put back"))
    ok = ok and not (workdir / "Duplicates").exists() and len(included(dup_moves, [0])) == 0
    lines.append("ok" if ok else "FAILED")
    return SelfTestReport(ok, lines)

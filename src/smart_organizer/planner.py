"""Turning a folder into a list of planned moves (nothing is touched here)."""

from __future__ import annotations

import calendar
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from .config import Config
from .duplicates import find_duplicates

LOG_DIR = ".organize"


@dataclass
class Move:
    """One planned file move."""

    src: Path
    dst: Path
    category: str
    size: int
    duplicate_of: Optional[Path] = None

    @property
    def renamed(self) -> bool:
        return self.src.name != self.dst.name


def _norm(path: Path) -> str:
    """Comparable form of a path (case-insensitive on Windows)."""
    return os.path.normcase(os.path.abspath(path))


def iter_files(root: Path, config: Config, recursive: bool = False) -> Iterator[Path]:
    """Files to organize under ``root``, skipping ignored files and our own log folder."""
    root = Path(root)
    skip_dirs = {LOG_DIR} | config.top_level_folders()
    if not recursive:
        for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_file() and not entry.is_symlink() and not config.is_ignored(entry.name):
                yield entry
        return
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        if here == root:
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        dirnames[:] = sorted(d for d in dirnames if not (config.skip_hidden and d.startswith(".")))
        for name in sorted(filenames, key=str.lower):
            p = here / name
            if not p.is_symlink() and not config.is_ignored(name):
                yield p


def date_folder(path: Path, config: Config) -> str:
    """Date part of the destination, from the file's modification time."""
    dt = datetime.fromtimestamp(path.stat().st_mtime)
    return config.date_format.format(year=dt.year, month=dt.month, day=dt.day,
                                     month_name=calendar.month_name[dt.month])


def unique_destination(dst: Path, taken: set[str]) -> Path:
    """Add " (1)", " (2)"... before the extension until the name is free."""
    candidate, n = dst, 1
    while _norm(candidate) in taken or candidate.exists():
        candidate = dst.with_name(f"{dst.stem} ({n}){dst.suffix}")
        n += 1
    return candidate


def build_plan(root: Path, config: Config, dest: Optional[Path] = None, mode: Optional[str] = None,
               recursive: bool = False) -> list[Move]:
    """Plan where every file should go. Returns only files that actually move."""
    root = Path(root).resolve()
    dest = Path(dest).resolve() if dest else root
    mode = mode or config.mode
    files = list(iter_files(root, config, recursive))

    dup_of: dict[str, Path] = {}
    if config.duplicates == "move":
        for group in find_duplicates(files):
            for extra in group[1:]:
                dup_of[_norm(extra)] = group[0]

    taken: set[str] = set()
    moves: list[Move] = []
    for f in files:
        size = f.stat().st_size
        if _norm(f) in dup_of:
            category, folder = "Duplicate", config.duplicates_folder
        else:
            category, folder = config.category_for(f.name, size)
            if mode == "date":
                folder = date_folder(f, config)
            elif mode == "type-date":
                folder = f"{folder}/{date_folder(f, config)}"
        target_dir = dest.joinpath(*[part for part in folder.split("/") if part])
        target = target_dir / f.name
        if _norm(target) == _norm(f):
            taken.add(_norm(f))
            continue
        target = unique_destination(target, taken)
        taken.add(_norm(target))
        moves.append(Move(src=f, dst=target, category=category, size=size, duplicate_of=dup_of.get(_norm(f))))
    return moves


def summarize(moves: list[Move]) -> dict[str, tuple[int, int]]:
    """``{category: (file count, total bytes)}`` sorted by count."""
    out: dict[str, list[int]] = {}
    for m in moves:
        c = out.setdefault(m.category, [0, 0])
        c[0] += 1
        c[1] += m.size
    return {k: (v[0], v[1]) for k, v in sorted(out.items(), key=lambda kv: (-kv[1][0], kv[0]))}


def human_size(n: float) -> str:
    """1536 -> '1.5 KB'."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

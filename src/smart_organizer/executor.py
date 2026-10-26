"""Applying a plan and undoing it from the JSON log."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Optional

from .planner import LOG_DIR, Move

LOG_VERSION = 1


@dataclass
class RunResult:
    """What happened during a run or an undo."""

    done: list[tuple[Path, Path]] = field(default_factory=list)
    failed: list[tuple[Path, str]] = field(default_factory=list)
    log_path: Optional[Path] = None


def to_log_path(path: Path, root: Path) -> str:
    """Store paths relative to the organized folder with forward slashes (portable)."""
    try:
        return Path(path).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return Path(path).resolve().as_posix()


def from_log_path(text: str, root: Path) -> Path:
    """Inverse of :func:`to_log_path`; also accepts Windows-style backslash paths."""
    pure = PureWindowsPath(text) if ("\\" in text or (len(text) > 1 and text[1] == ":")) else PurePosixPath(text)
    if pure.is_absolute():
        return Path(text)
    return root.joinpath(*pure.parts)


def _write_log(log_path: Path, root: Path, entries: list[dict], undone: bool = False) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": LOG_VERSION, "root": root.resolve().as_posix(),
               "created": datetime.now().isoformat(timespec="seconds"), "undone": undone, "moves": entries}
    tmp = log_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(log_path)


def apply_plan(moves: list[Move], root: Path, on_progress: Optional[Callable[[Move], None]] = None) -> RunResult:
    """Move the files and write an undo log to ``<root>/.organize/``."""
    root = Path(root).resolve()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    log_path = root / LOG_DIR / f"undo-{stamp}.json"
    result = RunResult(log_path=log_path)
    entries: list[dict] = []
    try:
        for m in moves:
            try:
                m.dst.parent.mkdir(parents=True, exist_ok=True)
                if m.dst.exists():
                    raise FileExistsError(f"{m.dst} already exists")
                shutil.move(str(m.src), str(m.dst))
                entries.append({"src": to_log_path(m.src, root), "dst": to_log_path(m.dst, root)})
                result.done.append((m.src, m.dst))
            except OSError as exc:
                result.failed.append((m.src, str(exc)))
            if on_progress:
                on_progress(m)
    finally:
        if entries:
            _write_log(log_path, root, entries)
        else:
            result.log_path = None
    return result


def list_logs(root: Path) -> list[Path]:
    """Undo logs in ``root``, newest first (already-undone logs excluded)."""
    folder = Path(root) / LOG_DIR
    if not folder.is_dir():
        return []
    logs = []
    for p in folder.glob("undo-*.json"):
        try:
            if not json.loads(p.read_text(encoding="utf-8")).get("undone"):
                logs.append(p)
        except (OSError, ValueError):
            continue
    return sorted(logs, reverse=True)


def _remove_empty_dirs(start: Path, stop: Path) -> None:
    """Delete now-empty folders from ``start`` upwards, never touching ``stop``."""
    current = start
    stop = stop.resolve()
    while current.resolve() != stop and stop in current.resolve().parents:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def undo(root: Path, log_path: Optional[Path] = None) -> RunResult:
    """Move files back to where they were, using the newest (or given) undo log."""
    root = Path(root).resolve()
    if log_path is None:
        logs = list_logs(root)
        if not logs:
            raise FileNotFoundError(f"No undo log found in {root / LOG_DIR}")
        log_path = logs[0]
    data = json.loads(Path(log_path).read_text(encoding="utf-8"))
    result = RunResult(log_path=Path(log_path))
    for entry in reversed(data["moves"]):
        src, dst = from_log_path(entry["src"], root), from_log_path(entry["dst"], root)
        try:
            if not dst.exists():
                raise FileNotFoundError(f"{dst} is gone (moved or deleted since)")
            if src.exists():
                raise FileExistsError(f"{src} exists again, not overwriting it")
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(src))
            result.done.append((dst, src))
            _remove_empty_dirs(dst.parent, root)
        except OSError as exc:
            result.failed.append((dst, str(exc)))
    _write_log(Path(log_path), root, data["moves"], undone=True)
    return result

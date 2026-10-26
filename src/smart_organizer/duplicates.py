"""Finding duplicate files by content (size first, then SHA-256)."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Iterable

CHUNK = 1024 * 1024


def file_hash(path: Path, limit: int | None = None) -> str:
    """SHA-256 of a file (or of its first ``limit`` bytes)."""
    h = hashlib.sha256()
    read = 0
    with open(path, "rb") as fh:
        while True:
            size = CHUNK if limit is None else min(CHUNK, limit - read)
            if size <= 0:
                break
            block = fh.read(size)
            if not block:
                break
            h.update(block)
            read += len(block)
    return h.hexdigest()


def find_duplicates(paths: Iterable[Path]) -> list[list[Path]]:
    """Groups of files with identical content. Each group is sorted oldest first.

    Files are first grouped by size (cheap), then by a hash of the first 64 KB,
    and only then fully hashed, so big folders stay fast.
    """
    by_size: dict[int, list[Path]] = defaultdict(list)
    for p in paths:
        by_size[p.stat().st_size].append(p)

    groups: list[list[Path]] = []
    for size, same_size in by_size.items():
        if len(same_size) < 2 or size == 0:
            continue
        by_head: dict[str, list[Path]] = defaultdict(list)
        for p in same_size:
            by_head[file_hash(p, limit=64 * 1024)].append(p)
        for candidates in by_head.values():
            if len(candidates) < 2:
                continue
            by_full: dict[str, list[Path]] = defaultdict(list)
            for p in candidates:
                by_full[file_hash(p) if size > 64 * 1024 else "head"].append(p)
            for group in by_full.values():
                if len(group) > 1:
                    groups.append(sorted(group, key=lambda q: (q.stat().st_mtime, q.name)))
    return sorted(groups, key=lambda g: g[0].name.lower())

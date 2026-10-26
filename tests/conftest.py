import os
import time
from pathlib import Path

import pytest


@pytest.fixture
def messy(tmp_path: Path) -> Path:
    """A small messy folder with known modification times."""
    files = {
        "photo.JPG": b"jpg-bytes",
        "Screenshot 2026-01-01.png": b"png-bytes",
        "song.mp3": b"mp3" * 10,
        "report.pdf": b"pdf" * 20,
        "report copy.pdf": b"pdf" * 20,  # duplicate of report.pdf
        "archive.zip": b"zip" * 5,
        "weird.xyz": b"???",
        "my notes ünïcode.txt": "héllo".encode(),
        ".hidden": b"secret",
        "desktop.ini": b"[.ShellClassInfo]",
    }
    base = time.mktime((2025, 3, 15, 12, 0, 0, 0, 0, -1))
    for i, (name, data) in enumerate(files.items()):
        p = tmp_path / name
        p.write_bytes(data)
        os.utime(p, (base + i, base + i))
    return tmp_path

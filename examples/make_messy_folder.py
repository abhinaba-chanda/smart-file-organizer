"""Create a messy, Downloads-like folder to try the organizer on safely.

    python examples/make_messy_folder.py demo-downloads
    organize preview demo-downloads
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

FILES = {
    "holiday photo.jpg": 180_000, "IMG_2041.HEIC": 950_000, "Screenshot 2026-10-02 at 09.14.png": 240_000,
    "Screenshot 2026-10-11 at 18.40.png": 260_000, "meme.gif": 90_000, "logo.svg": 4_000,
    "match highlights.mp4": 3_500_000, "song.mp3": 900_000, "voice note.m4a": 120_000,
    "resume.pdf": 85_000, "notes.txt": 2_000, "assignment.docx": 40_000, "budget.xlsx": 22_000,
    "marks.csv": 3_000, "slides.pptx": 300_000, "project.zip": 1_200_000, "python-installer.exe": 2_000_000,
    "script.py": 1_500, "index.html": 2_200, "data.json": 5_000, "Roboto.ttf": 160_000, "mystery.xyz": 1_000,
}
DUPLICATES = {"holiday photo (1).jpg": "holiday photo.jpg", "resume - copy.pdf": "resume.pdf"}


def main(target: str = "demo-downloads") -> None:
    root = Path(target)
    root.mkdir(parents=True, exist_ok=True)
    now = time.time()
    for i, (name, size) in enumerate(FILES.items()):
        p = root / name
        p.write_bytes(name.encode() * (size // max(1, len(name))))
        when = now - i * 9 * 86400  # spread files over the last months
        os.utime(p, (when, when))
    for copy, original in DUPLICATES.items():
        (root / copy).write_bytes((root / original).read_bytes())
    print(f"Created {len(FILES) + len(DUPLICATES)} files in {root.resolve()}")


if __name__ == "__main__":
    main(*sys.argv[1:2])

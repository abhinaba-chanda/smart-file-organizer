import subprocess
import sys
from pathlib import Path

from rich.console import Console

from smart_organizer.cli import main


def run(*args: str) -> tuple[int, str]:
    console = Console(record=True, width=120, force_terminal=False)
    code = main(list(args), console=console)
    return code, console.export_text()


def test_preview_shows_plan_and_moves_nothing(messy: Path):
    before = sorted(p.name for p in messy.iterdir())
    code, out = run("preview", str(messy))
    assert code == 0
    assert "DRY RUN" in out and "Music/song.mp3" in out and "Nothing was moved" in out
    assert sorted(p.name for p in messy.iterdir()) == before


def test_run_yes_and_undo(messy: Path):
    code, out = run("run", str(messy), "--yes")
    assert code == 0 and "Moved" in out
    assert (messy / "Music" / "song.mp3").exists()
    code, out = run("undo", str(messy))
    assert code == 0 and "Restored" in out
    assert (messy / "song.mp3").exists()


def test_run_dry_run_flag(messy: Path):
    code, out = run("run", str(messy), "--dry-run")
    assert code == 0 and "DRY RUN" in out
    assert (messy / "song.mp3").exists()


def test_dupes(messy: Path):
    code, out = run("dupes", str(messy))
    assert code == 0 and "report copy.pdf" in out and "extra copies" in out


def test_init_config_and_local_config_is_used(messy: Path):
    code, _ = run("init-config", str(messy))
    assert code == 0 and (messy / "organizer.yaml").exists()
    (messy / "organizer.yaml").write_text("rules:\n  - name: Tunes\n    folder: Tunes\n    extensions: [mp3]\n",
                                          encoding="utf-8")
    code, out = run("preview", str(messy))
    assert "Tunes/song.mp3" in out


def test_bad_config_is_reported(messy: Path):
    bad = messy / "bad.yaml"
    bad.write_text("mode: sideways\n", encoding="utf-8")
    code, out = run("preview", str(messy), "--config", str(bad))
    assert code == 1 and "Config error" in out


def test_installed_command_runs(messy: Path):
    r = subprocess.run([sys.executable, "-m", "smart_organizer", "preview", str(messy)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert "song.mp3" in r.stdout


def test_guided_mode_previews_then_organizes(messy: Path, monkeypatch):
    from smart_organizer.cli import guided

    answers = iter(["organize", f'"{messy}"', "type", "y"])
    monkeypatch.setattr("builtins.input", lambda *a, **k: next(answers))
    console = Console(record=True, width=120, force_terminal=False)
    code = guided(console)
    out = console.export_text()
    assert code == 0
    assert "DRY RUN" in out and "Moved" in out
    assert (messy / "Music" / "song.mp3").exists()


def test_guided_mode_quit_changes_nothing(messy: Path, monkeypatch):
    from smart_organizer.cli import guided

    before = sorted(p.name for p in messy.iterdir())
    monkeypatch.setattr("builtins.input", lambda *a, **k: "quit")
    assert guided(Console(record=True, width=120, force_terminal=False)) == 0
    assert sorted(p.name for p in messy.iterdir()) == before


def test_version_is_V1(monkeypatch):
    from smart_organizer import __version__
    from smart_organizer.cli import guided

    assert __version__ == "V1"
    r = subprocess.run([sys.executable, "-m", "smart_organizer", "--version"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().endswith(" V1")
    monkeypatch.setattr("builtins.input", lambda *a, **k: "quit")
    console = Console(record=True, width=120, force_terminal=False)
    guided(console)
    assert "Smart File Organizer V1" in console.export_text()

"""Entry point for the Windows .exe built with PyInstaller (see .github/workflows/release.yml)."""

from smart_organizer.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

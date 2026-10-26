"""The exe's Windows file info (Properties -> Details) names the publisher."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "packaging" / "version_info.txt"


def _strings():
    # The file is a PyInstaller VSVersionInfo literal; read its StringStruct pairs.
    from ast import literal_eval
    import re

    text = VERSION_FILE.read_text(encoding="utf-8")
    pairs = re.findall(r"StringStruct\(('[^']*'),\s*('[^']*')\)", text)
    return {literal_eval(k): literal_eval(v) for k, v in pairs}


def test_version_file_names_publisher_without_links():
    s = _strings()
    assert s["CompanyName"] == "Abhinaba-Dev"
    assert s["LegalCopyright"] == "\u00a9 2026 Abhinaba-Dev"
    assert "Comments" not in s
    for key, value in s.items():
        assert "github.com" not in value.lower(), key
    assert "github.com" not in VERSION_FILE.read_text(encoding="utf-8").lower()
    assert s["ProductVersion"] == "V1"
    assert s["FileVersion"] == "V1"
    assert s["ProductName"] == "Smart File Organizer"
    assert s["OriginalFilename"] == "SmartFileOrganizer.exe"


def test_release_build_uses_version_file():
    wf = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    spec = (ROOT / "packaging" / "SmartFileOrganizer.spec").read_text(encoding="utf-8")
    assert "packaging/SmartFileOrganizer.spec" in wf
    assert '"version_info.txt"' in spec and '"icon.ico"' in spec
    assert "console=False" in spec  # windowed: no cmd window

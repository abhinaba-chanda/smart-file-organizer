"""The exe's Windows file info (Properties -> Details) names the publisher."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "packaging" / "version_info.txt"
GITHUB = "https://github.com/abhinaba-chanda"


def _strings():
    # The file is a PyInstaller VSVersionInfo literal; read its StringStruct pairs.
    from ast import literal_eval
    import re

    text = VERSION_FILE.read_text(encoding="utf-8")
    pairs = re.findall(r"StringStruct\(('[^']*'),\s*('[^']*')\)", text)
    return {literal_eval(k): literal_eval(v) for k, v in pairs}


def test_version_file_names_publisher_and_github_link():
    s = _strings()
    assert s["CompanyName"] == "Abhinaba-Dev"
    assert GITHUB in s["LegalCopyright"]
    assert "Abhinaba-Dev" in s["LegalCopyright"]
    assert s["Comments"] == GITHUB
    assert s["ProductVersion"] == "V1"
    assert s["FileVersion"] == "V1"
    assert s["ProductName"] == "Smart File Organizer"
    assert s["OriginalFilename"] == "SmartFileOrganizer.exe"


def test_release_build_uses_version_file():
    wf = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "--version-file packaging/version_info.txt" in wf

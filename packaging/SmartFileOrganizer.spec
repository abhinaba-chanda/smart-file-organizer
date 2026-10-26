# PyInstaller spec for the small, windowed SmartFileOrganizer.exe (see .github/workflows/release.yml).
# Build:  pyinstaller --noconfirm --clean packaging/SmartFileOrganizer.spec  [--upx-dir <upx folder>]
import os
import sys

HERE = os.path.abspath(SPECPATH)
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from PyInstaller.utils.hooks import collect_data_files  # noqa: E402

# Standard-library parts the window never uses. Leaving them out keeps the exe small.
EXCLUDES = [
    "rich", "pygments", "markdown_it", "mdurl",  # terminal-only (the CLI), not needed by the window
    "unittest", "doctest", "pdb", "pydoc", "pydoc_data", "test", "tkinter.test", "idlelib", "lib2to3",
    "email", "http", "xml", "xmlrpc", "html", "urllib.request", "ftplib", "smtplib", "imaplib", "poplib", "mailbox",
    "asyncio", "concurrent", "multiprocessing", "socketserver", "ssl", "_ssl", "_hashlib", "socket", "select",
    "selectors", "sqlite3", "_sqlite3", "bz2", "_bz2", "lzma", "_lzma", "decimal", "_decimal", "pyexpat",
    "curses", "readline", "distutils", "setuptools", "pkg_resources", "pip", "yaml._yaml", "_yaml",
    "zipimport_tests", "turtle", "turtledemo", "wsgiref", "venv", "ensurepip", "csv", "_csv", "statistics",
    "difflib", "optparse", "getopt", "gettext", "tarfile", "zipapp", "plistlib", "tomllib", "_tomllib",
    "PIL", "numpy",
]

a = Analysis(
    [os.path.join(HERE, "gui_launcher.py")],
    pathex=[os.path.join(ROOT, "src")],
    datas=collect_data_files("smart_organizer") + collect_data_files("sv_ttk")
    + [(os.path.join(HERE, "icon.ico"), ".")],
    hiddenimports=["sv_ttk"],
    excludes=EXCLUDES,
    optimize=2,
)

# Tcl/Tk ships time zones, translations, demos and dozens of text encodings the window never uses.
DROP = ("tzdata", "msgs", "demos", "images", "http1.0", "opt0.4", "dde1.4", "reg1.3", "tcltest")
KEEP_ENC = {"ascii.enc", "cp1252.enc", "iso8859-1.enc", "cp437.enc", "cp850.enc"}


def keep(dest):
    parts = dest.replace("\\", "/").split("/")
    if parts[0] in ("_tcl_data", "_tk_data", "tcl", "tk", "tcl8"):
        if any(p in DROP for p in parts[1:-1]):
            return False
        if "encoding" in parts[1:-1] and parts[-1] not in KEEP_ENC:
            return False
    return True


a.datas = [d for d in a.datas if keep(d[0])]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SmartFileOrganizer",
    icon=os.path.join(HERE, "icon.ico"),
    version=os.path.join(HERE, "version_info.txt"),
    console=False,
    debug=False,
    strip=sys.platform != "win32",
    upx=True,  # used only when UPX is available (the workflow downloads it)
    upx_exclude=["vcruntime140.dll", "vcruntime140_1.dll", "python3.dll", "python312.dll", "ucrtbase.dll"],
    runtime_tmpdir=None,
)

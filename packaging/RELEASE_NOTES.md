# Smart File Organizer {{TAG}} for Windows

Tidy a messy folder (like Downloads) by file type and/or date. It shows a dry-run preview first, asks before moving anything, can undo the last run, finds duplicate files, and supports your own YAML rules.

## Download and run

1. Download **SmartFileOrganizer.exe** below (or the zip, which also has the README). No Python or installer needed.
2. **Double-click it.** It opens in guided mode: pick *organize*, drag your folder into the window (or press Enter for your Downloads folder), check the preview, then confirm.
3. Or run it from Command Prompt / PowerShell with arguments:

```
SmartFileOrganizer.exe preview "C:\Users\you\Downloads"
SmartFileOrganizer.exe run "C:\Users\you\Downloads" --mode type-date
SmartFileOrganizer.exe undo "C:\Users\you\Downloads"
SmartFileOrganizer.exe dupes "C:\Users\you\Downloads"
SmartFileOrganizer.exe --help
```

## Windows SmartScreen

The exe is not code-signed, so Windows may show "Windows protected your PC". Click **More info** and then **Run anyway**. It is built from this repository's source by GitHub Actions (see the workflow run linked to this release), and you can compare the checksum below.

## Checksum

SmartFileOrganizer.exe ({{SIZE}}), SHA-256:

```
{{SHA256}}
```

All files are listed in `SHA256SUMS.txt`. To check on Windows: `certutil -hashfile SmartFileOrganizer.exe SHA256`

## Source code

The source for this exact version is attached below as **Source code (zip)** and **Source code (tar.gz)**. With Python 3.9+ you can also `pip install .` and use the `organize` command.

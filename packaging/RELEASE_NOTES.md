# Smart File Organizer {{TAG}} for Windows

Tidy a messy folder (like Downloads) by file type and/or date, in a simple app window. It shows a preview first, moves nothing until you click Organize, can undo the last run, and finds duplicate files.

## Download and run

1. Download **SmartFileOrganizer.exe** below ({{SIZE}}, or the zip, which also has the README). No Python or installer needed.
2. **Double-click it.** A small window opens (no cmd window), starting on your Downloads folder.
3. Pick how to group (by type, by date, or type + date; tick **Subfolders** to go deeper), check the preview (untick any file to skip it), then click **Organize** and use **Open folder** in the done message. **Undo last run** puts everything back; **Find duplicates** lists extra copies and can move them into a Duplicates folder (nothing is deleted).

It follows your Windows light/dark setting and remembers your last folder and choices. The **GitHub** button at the top links to the author's profile.

## Windows SmartScreen

The exe is not code-signed, so Windows may show "Windows protected your PC". Click **More info** and then **Run anyway**. It is built from this repository's source by GitHub Actions ([build log]({{RUN_URL}})), and you can compare the checksum below.

## Checksum

SmartFileOrganizer.exe ({{SIZE}}), SHA-256:

```
{{SHA256}}
```

All files are listed in `SHA256SUMS.txt`. To check on Windows: `certutil -hashfile SmartFileOrganizer.exe SHA256`

## Source code and command line

The source for this exact version is attached below as **Source code (zip)** and **Source code (tar.gz)**. With Python 3.9+ you can `pip install .` and use the `organize` command (`organize preview "C:\Users\you\Downloads"`, `organize run …`, `organize undo …`, `organize dupes …`) or `organize-gui` for the window.

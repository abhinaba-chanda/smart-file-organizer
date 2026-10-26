"""The desktop window: pick a folder, preview, organize, undo. Built on tkinter/ttk only.

Start it with ``python -m smart_organizer.gui`` (or the ``organize-gui`` command / the Windows .exe).
"""

from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from . import gui_logic as logic

PAD = 16


def _enable_dpi_awareness() -> None:
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


def _dark_title_bar(window: tk.Tk, dark: bool) -> None:
    """Match the Windows 11 title bar to the theme (no-op elsewhere)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new, old)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except Exception:
        pass


class App:
    """The main window."""

    def __init__(self, root: tk.Tk, folder: Optional[Path] = None, auto_preview: bool = True):
        self.root = root
        self.dark = logic.system_prefers_dark()
        self.folder = tk.StringVar(value=str(folder or logic.default_folder()))
        self.mode = tk.StringVar(value="type")
        self.status = tk.StringVar(value="Pick a folder to tidy.")
        self.moves: list = []
        self.busy = False
        self.events: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._toast_job: Optional[str] = None

        self._setup_window()
        self._build()
        self.root.after(50, self._drain_events)
        if auto_preview:
            self.root.after(150, self.preview)

    # ---------- look ----------
    def _setup_window(self) -> None:
        root = self.root
        root.title(logic.APP_TITLE)
        icon = logic.resource_path("icon.ico")
        if icon and sys.platform == "win32":
            try:
                root.iconbitmap(default=str(icon))
            except tk.TclError:
                pass
        try:
            import sv_ttk  # Windows 11 "Sun Valley" look for ttk (tiny, pure Tcl)

            sv_ttk.set_theme("dark" if self.dark else "light", root)
        except Exception:
            ttk.Style(root).theme_use("vista" if sys.platform == "win32" else "clam")
        style = ttk.Style(root)
        family = "Segoe UI" if sys.platform == "win32" else "Selawik"
        self.fg_muted = "#9a9a9a" if self.dark else "#6b6b6b"
        style.configure("Title.TLabel", font=(family + " Semibold", 15))
        style.configure("Muted.TLabel", font=(family, 9), foreground=self.fg_muted)
        style.configure("Status.TLabel", font=(family, 10))
        style.configure("Footer.TLabel", font=(family, 8), foreground=self.fg_muted)
        style.configure("Treeview", rowheight=26)
        scale = root.winfo_fpixels("1i") / 96.0
        w, h = int(520 * scale), int(420 * scale)
        root.geometry(f"{w}x{h}")
        root.minsize(int(460 * scale), int(380 * scale))
        _dark_title_bar(root, self.dark)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=(PAD, PAD - 2, PAD, 6))
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text=logic.APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Tidy a messy folder by type or date. Nothing moves until you say so.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 10))

        row = ttk.Frame(outer)
        row.pack(fill="x")
        self.entry = ttk.Entry(row, textvariable=self.folder)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _e: self.preview())
        self.browse_btn = ttk.Button(row, text="Browse\u2026", command=self.browse)
        self.browse_btn.pack(side="left", padx=(8, 0))

        modes = ttk.Frame(outer)
        modes.pack(fill="x", pady=(10, 8))
        ttk.Label(modes, text="Group", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        self.mode_buttons = []
        for key, label in logic.MODE_LABELS.items():
            b = ttk.Radiobutton(modes, text=label, value=key, variable=self.mode, command=self.preview)
            b.pack(side="left", padx=(0, 12))
            self.mode_buttons.append(b)

        # bottom rows first, so the list gives up space instead of pushing the buttons off a small window
        ttk.Label(outer, text=logic.FOOTER, style="Footer.TLabel").pack(side="bottom", anchor="e", pady=(6, 0))
        actions = ttk.Frame(outer)
        actions.pack(side="bottom", fill="x", pady=(2, 0))
        self.dupes_btn = ttk.Button(actions, text="Find duplicates", command=self.find_dupes)
        self.dupes_btn.pack(side="left")
        self.undo_btn = ttk.Button(actions, text="Undo last run", command=self.undo)
        self.undo_btn.pack(side="left", padx=(8, 0))
        self.organize_btn = ttk.Button(actions, text="Organize", style="Accent.TButton", command=self.organize)
        self.organize_btn.pack(side="right")
        self.preview_btn = ttk.Button(actions, text="Preview", command=self.preview)
        self.preview_btn.pack(side="right", padx=(0, 8))
        statusbox = ttk.Frame(outer)
        statusbox.pack(side="bottom", fill="x", pady=(8, 6))
        self.status_label = ttk.Label(statusbox, textvariable=self.status, style="Status.TLabel")
        self.status_label.pack(side="bottom", anchor="w")
        self.progress = ttk.Progressbar(statusbox, mode="determinate")

        table = ttk.Frame(outer)
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("file", "dest"), show="headings", selectmode="none", height=4)
        self.tree.heading("file", text="File", anchor="w")
        self.tree.heading("dest", text="Goes to", anchor="w")
        self.tree.column("file", width=230, anchor="w")
        self.tree.column("dest", width=190, anchor="w")
        bar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        self.toast = tk.Label(self.root, text="", bg="#0f7b0f" if not self.dark else "#2e9e46", fg="white",
                              font=("Segoe UI" if sys.platform == "win32" else "Selawik", 10), padx=14, pady=6)
        self._refresh_buttons()

    # ---------- helpers ----------
    def current_folder(self) -> Optional[Path]:
        p = Path(self.folder.get().strip().strip('"')).expanduser()
        if not p.is_dir():
            self.show_error(NotADirectoryError(str(p)))
            return None
        return p.resolve()

    def _refresh_buttons(self) -> None:
        folder = Path(self.folder.get().strip().strip('"')).expanduser()
        idle = "disabled" if self.busy else "normal"
        for b in (self.browse_btn, self.preview_btn, self.dupes_btn, *self.mode_buttons):
            b.configure(state=idle)
        self.organize_btn.configure(state="normal" if (self.moves and not self.busy) else "disabled")
        self.undo_btn.configure(state="normal" if (not self.busy and folder.is_dir() and logic.can_undo(folder))
                                else "disabled")

    def fill(self, rows: list[tuple[str, str]]) -> None:
        self.tree.delete(*self.tree.get_children())
        for a, b in rows:
            self.tree.insert("", "end", values=(a, b))

    def show_toast(self, text: str) -> None:
        self.toast.configure(text=f"\u2713  {text}")
        self.toast.place(relx=0.5, rely=1.0, y=-70, anchor="s")
        self.toast.lift()
        if self._toast_job:
            self.root.after_cancel(self._toast_job)
        self._toast_job = self.root.after(2600, self.toast.place_forget)

    def show_error(self, exc: BaseException) -> None:
        messagebox.showerror(logic.APP_TITLE, logic.friendly_error(exc), parent=self.root)

    def _run_bg(self, name: str, work: Callable[[], object]) -> None:
        """Run ``work`` off the UI thread; its result comes back through the event queue."""
        self.busy = True
        self._refresh_buttons()

        def target() -> None:
            try:
                self.events.put((name, work()))
            except BaseException as exc:  # shown as a friendly dialog
                self.events.put(("error", exc))

        threading.Thread(target=target, daemon=True).start()

    def _drain_events(self) -> None:
        try:
            while True:
                name, payload = self.events.get_nowait()
                getattr(self, f"_on_{name}")(payload)
        except queue.Empty:
            pass
        self.root.after(50, self._drain_events)

    # ---------- actions ----------
    def browse(self) -> None:
        chosen = filedialog.askdirectory(parent=self.root, initialdir=self.folder.get(), title="Choose a folder to tidy")
        if chosen:
            self.folder.set(str(Path(chosen)))
            self.preview()

    def preview(self) -> None:
        if self.busy:
            return
        folder = self.current_folder()
        if folder is None:
            return
        self.status.set("Looking through the folder\u2026")
        mode = self.mode.get()
        self._run_bg("preview", lambda: (folder, logic.make_plan(folder, mode)))

    def _on_preview(self, payload) -> None:
        folder, moves = payload
        self.busy = False
        self.moves = moves
        self.fill(logic.preview_rows(moves, folder))
        self.status.set(logic.plan_summary(moves))
        self._refresh_buttons()

    def organize(self) -> None:
        if self.busy or not self.moves:
            return
        folder = self.current_folder()
        if folder is None:
            return
        n = len(self.moves)
        if not messagebox.askyesno(logic.APP_TITLE, f"Move {n} file{'s' if n != 1 else ''} into folders?\n"
                                   "You can put everything back with Undo.", parent=self.root):
            return
        moves = self.moves
        self.progress.configure(maximum=n, value=0)
        self.progress.pack(side="top", fill="x", pady=(0, 6))
        self.status.set("Organizing\u2026")
        self._run_bg("organized", lambda: logic.organize(moves, folder,
                                                         on_progress=lambda m: self.events.put(("step", m))))

    def _on_step(self, _move) -> None:
        self.progress.step(1)

    def _on_organized(self, result) -> None:
        self.busy = False
        self.progress.pack_forget()
        self.show_toast(logic.run_summary(result))
        self.moves = []
        self.preview()

    def undo(self) -> None:
        if self.busy:
            return
        folder = self.current_folder()
        if folder is None:
            return
        self.status.set("Putting files back\u2026")
        self._run_bg("undone", lambda: logic.undo_last(folder))

    def _on_undone(self, result) -> None:
        self.busy = False
        self.show_toast(logic.run_summary(result, "Put back"))
        self.preview()

    def find_dupes(self) -> None:
        if self.busy:
            return
        folder = self.current_folder()
        if folder is None:
            return
        self.status.set("Checking file contents\u2026")
        self._run_bg("dupes", lambda: logic.duplicate_rows(folder))

    def _on_dupes(self, payload) -> None:
        rows, text = payload
        self.busy = False
        self.moves = []
        self.fill(rows)
        self.status.set(text)
        self._refresh_buttons()

    def _on_error(self, exc: BaseException) -> None:
        self.busy = False
        self.progress.pack_forget()
        self.status.set("")
        self._refresh_buttons()
        self.show_error(exc)


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--self-test"]:  # used by the release workflow on the built .exe
        import tempfile

        out = Path(argv[1]) if len(argv) > 1 else None
        try:
            report = logic.self_test(Path(tempfile.mkdtemp(prefix="sfo-selftest-")))
            root = tk.Tk()
            root.withdraw()
            App(root, auto_preview=False)
            root.update()
            root.destroy()
            lines = report.lines + ["window ok"]
            code = 0 if report.ok else 1
        except BaseException as exc:
            lines, code = [f"FAILED: {exc!r}"], 1
        if out:
            out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return code
    _enable_dpi_awareness()
    root = tk.Tk()
    App(root, folder=logic.folder_from_argv(argv))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

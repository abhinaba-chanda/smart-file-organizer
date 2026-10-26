"""Command-line interface: ``organize``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.prompt import Confirm, Prompt

from . import __version__
from .config import CONFIG_NAME, MODES, ConfigError, default_config_text, find_config, load_config
from .duplicates import find_duplicates
from .executor import apply_plan, list_logs, undo
from .planner import build_plan, iter_files
from .ui import destination_tree, duplicates_table, header, human_size, plan_table, summary_table


def _console() -> Console:
    return Console(highlight=False)


def _find_config(folder: Path, explicit: Optional[str]) -> Optional[Path]:
    """--config wins; otherwise use organizer.yaml in the folder if present."""
    return find_config(folder, explicit)


def _folder(value: str) -> Path:
    p = Path(value).expanduser()
    if not p.is_dir():
        raise argparse.ArgumentTypeError(f"'{value}' is not a folder")
    return p.resolve()


def _shown(args: argparse.Namespace) -> str:
    """The folder as the user typed it (quoted if it has spaces), for hints."""
    raw = getattr(args, "folder_arg", None) or str(args.folder)
    return f'"{raw}"' if " " in raw else raw


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="organize",
        description="Tidy a messy folder (like Downloads) by file type and/or date, safely.",
        epilog="Start with:  organize preview ~/Downloads",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("folder", type=_folder, help="folder to organize, e.g. ~/Downloads")
        p.add_argument("-c", "--config", help=f"YAML rules file (default: {CONFIG_NAME} in the folder, "
                                              "else built-in rules)")
        p.add_argument("-m", "--mode", choices=MODES, help="group by type, date or type-date")
        p.add_argument("-d", "--dest", type=Path, help="put organized files here instead of in the folder")
        p.add_argument("-r", "--recursive", action="store_true", help="also organize files in sub-folders")
        p.add_argument("--duplicates", choices=["keep", "move"], help="move extra copies of identical files "
                                                                      "into a Duplicates folder")

    p = sub.add_parser("preview", help="show what would happen (changes nothing)")
    common(p)
    p.add_argument("--all", action="store_true", help="list every planned move")

    p = sub.add_parser("run", help="organize the folder (asks first)")
    common(p)
    p.add_argument("-y", "--yes", action="store_true", help="don't ask for confirmation")
    p.add_argument("-n", "--dry-run", action="store_true", help="same as preview")

    p = sub.add_parser("undo", help="put files back using the latest undo log")
    p.add_argument("folder", type=_folder)
    p.add_argument("--log", type=Path, help="a specific undo log file")
    p.add_argument("--list", action="store_true", help="list available undo logs")

    p = sub.add_parser("dupes", help="find duplicate files by content hash")
    p.add_argument("folder", type=_folder)
    p.add_argument("-r", "--recursive", action="store_true")
    p.add_argument("-c", "--config")

    p = sub.add_parser("init-config", help=f"write the default rules to {CONFIG_NAME} so you can edit them")
    p.add_argument("folder", type=_folder, nargs="?", default=Path.cwd())
    p.add_argument("--force", action="store_true", help="overwrite an existing file")
    return parser


def _plan(args: argparse.Namespace, console: Console):
    cfg = load_config(_find_config(args.folder, args.config))
    if args.duplicates:
        cfg.duplicates = args.duplicates
    with console.status("Scanning files…", spinner="dots"):
        moves = build_plan(args.folder, cfg, dest=args.dest, mode=args.mode, recursive=args.recursive)
    return cfg, moves


def cmd_preview(args: argparse.Namespace, console: Console) -> int:
    _, moves = _plan(args, console)
    header(console, "Preview", args.folder, dry_run=True)
    if not moves:
        console.print("[green]✨ Nothing to do, the folder is already tidy.[/]")
        return 0
    root = (args.dest or args.folder).resolve()
    console.print(plan_table(moves, root, limit=len(moves) if args.all else 25))
    console.print(summary_table(moves))
    console.print(destination_tree(moves, root))
    console.print(f"\n[yellow]Nothing was moved.[/] Run [bold]organize run {_shown(args)}[/] to do it "
                  "(you can undo it any time with [bold]organize undo[/]).")
    return 0


def cmd_run(args: argparse.Namespace, console: Console) -> int:
    if args.dry_run:
        args.all = False
        return cmd_preview(args, console)
    _, moves = _plan(args, console)
    header(console, "Organize", args.folder, dry_run=False)
    if not moves:
        console.print("[green]✨ Nothing to do, the folder is already tidy.[/]")
        return 0
    console.print(summary_table(moves))
    if not args.yes and not Confirm.ask(f"Move [bold]{len(moves)}[/] files?", console=console, default=False):
        console.print("Cancelled, nothing was moved.")
        return 1
    with Progress(TextColumn("[cyan]Moving"), BarColumn(), MofNCompleteColumn(), TextColumn("{task.description}"),
                  console=console, transient=True) as progress:
        task = progress.add_task("", total=len(moves))
        result = apply_plan(moves, args.folder, on_progress=lambda m: progress.update(
            task, advance=1, description=m.src.name[:40]))
    console.print(f"[bold green]✔ Moved {len(result.done)} files[/]"
                  f" ({human_size(sum(m.size for m in moves))}).")
    for src, err in result.failed:
        console.print(f"[red]✘ {src.name}: {err}[/]")
    if result.log_path:
        log = result.log_path.relative_to(args.folder).as_posix()
        console.print(f"[dim]Undo log saved to {log}[/]\nChanged your mind? [bold]organize undo {_shown(args)}[/]")
    return 0 if not result.failed else 2


def cmd_undo(args: argparse.Namespace, console: Console) -> int:
    if args.list:
        logs = list_logs(args.folder)
        if not logs:
            console.print("No undo logs.")
        for p in logs:
            console.print(f"• {p.name}")
        return 0
    try:
        result = undo(args.folder, args.log)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/]")
        return 1
    console.print(f"[bold green]↩ Restored {len(result.done)} files[/] from {result.log_path.name}")
    for path, err in result.failed:
        console.print(f"[yellow]! {path.name}: {err}[/]")
    return 0 if not result.failed else 2


def cmd_dupes(args: argparse.Namespace, console: Console) -> int:
    cfg = load_config(_find_config(args.folder, args.config))
    with console.status("Hashing files…", spinner="dots"):
        groups = find_duplicates(list(iter_files(args.folder, cfg, args.recursive)))
    if not groups:
        console.print("[green]No duplicates found.[/]")
        return 0
    console.print(duplicates_table(groups, args.folder))
    wasted = sum(g[0].stat().st_size * (len(g) - 1) for g in groups)
    console.print(f"[bold]{sum(len(g) - 1 for g in groups)}[/] extra copies wasting [bold]{human_size(wasted)}[/]. "
                  f"Move them aside with [bold]organize run {_shown(args)} --duplicates move[/].")
    return 0


def cmd_init(args: argparse.Namespace, console: Console) -> int:
    target = args.folder / CONFIG_NAME
    if target.exists() and not args.force:
        console.print(f"[yellow]{target} already exists (use --force to overwrite).[/]")
        return 1
    target.write_text(default_config_text(), encoding="utf-8")
    console.print(f"[green]Wrote {target}[/]. Edit the rules, then run [bold]organize preview {_shown(args)}[/].")
    return 0


GUIDED_ACTIONS = {"organize": "tidy a folder (shows a preview first)", "undo": "put the last organize back",
                  "dupes": "find duplicate files", "quit": "close"}


def _clean_path(text: str) -> str:
    """Strip the quotes Windows adds when a folder is dragged into the console."""
    return text.strip().strip('"').strip("'").strip()


def guided(console: Console, parser: Optional[argparse.ArgumentParser] = None) -> int:
    """Interactive mode, used when the program is started with no arguments (e.g. a double-clicked .exe)."""
    parser = parser or build_parser()
    console.print(f"[bold cyan]Smart File Organizer {__version__}[/] [dim]guided mode[/]")
    console.print("[dim]Tip: you can drag a folder into this window instead of typing its path. "
                  "Run with --help to see the command-line options.[/]\n")
    for name, text in GUIDED_ACTIONS.items():
        console.print(f"  [bold]{name}[/]  {text}")
    action = Prompt.ask("\nWhat do you want to do", choices=list(GUIDED_ACTIONS), default="organize",
                        console=console)
    if action == "quit":
        return 0
    default_folder = Path.home() / "Downloads"
    while True:
        raw = _clean_path(Prompt.ask("Folder", default=str(default_folder), console=console))
        folder = Path(raw).expanduser()
        if folder.is_dir():
            break
        console.print(f"[red]'{raw}' is not a folder, try again.[/]")
    if action == "undo":
        return COMMANDS["undo"](parser.parse_args(["undo", str(folder)]), console)
    if action == "dupes":
        return COMMANDS["dupes"](parser.parse_args(["dupes", str(folder)]), console)
    mode = Prompt.ask("Group files by", choices=list(MODES), default="type", console=console)
    code = cmd_preview(parser.parse_args(["preview", str(folder), "-m", mode]), console)
    if code != 0:
        return code
    return cmd_run(parser.parse_args(["run", str(folder), "-m", mode]), console)


def _pause_before_close(console: Console) -> None:
    """Keep a double-clicked console window open long enough to read the result."""
    try:
        console.input("\n[dim]Press Enter to close…[/]")
    except (EOFError, KeyboardInterrupt):
        pass


COMMANDS = {"preview": cmd_preview, "run": cmd_run, "undo": cmd_undo, "dupes": cmd_dupes, "init-config": cmd_init}


def main(argv: Optional[list[str]] = None, console: Optional[Console] = None) -> int:
    """Entry point for the ``organize`` command."""
    if sys.platform == "win32":  # make emoji and box characters print on older Windows consoles
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
            except (AttributeError, ValueError):
                pass
    parser = build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if argv is None and not raw_argv and sys.stdin is not None and sys.stdin.isatty():
        console = console or _console()
        try:
            code = guided(console, parser)
        except ConfigError as exc:
            console.print(f"[red]Config error:[/] {exc}")
            code = 1
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped.[/]")
            code = 130
        if getattr(sys, "frozen", False):
            _pause_before_close(console)
        return code
    args = parser.parse_args(raw_argv)
    folder_pos = [a for a in raw_argv[1:] if not a.startswith("-")]
    if hasattr(args, "folder") and folder_pos and Path(folder_pos[0]).expanduser().resolve() == args.folder:
        args.folder_arg = folder_pos[0]
    console = console or _console()
    try:
        return COMMANDS[args.command](args, console)
    except ConfigError as exc:
        console.print(f"[red]Config error:[/] {exc}")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped.[/]")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

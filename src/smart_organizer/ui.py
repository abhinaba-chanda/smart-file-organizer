"""Rich terminal output: tables, trees and colours."""

from __future__ import annotations

from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from .planner import Move, human_size, summarize  # noqa: F401  (human_size re-exported)

ICONS = {
    "Images": "🖼️ ", "Screenshots": "📸", "Videos": "🎬", "Music": "🎵", "Documents": "📄",
    "Spreadsheets": "📊", "Presentations": "📽️ ", "Archives": "🗜️ ", "Installers": "💿", "Code": "💻",
    "Fonts": "🔤", "Big files": "🐘", "Duplicate": "♊", "Other": "📦",
}
COLORS = {
    "Images": "magenta", "Screenshots": "bright_magenta", "Videos": "red", "Music": "green",
    "Documents": "cyan", "Spreadsheets": "bright_green", "Presentations": "yellow", "Archives": "bright_yellow",
    "Installers": "bright_red", "Code": "bright_blue", "Fonts": "white", "Big files": "bright_white",
    "Duplicate": "bright_black", "Other": "grey62",
}


def style_for(category: str) -> str:
    return COLORS.get(category, "white")


def header(console: Console, title: str, folder: Path, dry_run: bool) -> None:
    badge = Text(" DRY RUN ", style="bold black on yellow") if dry_run else Text(" LIVE ", style="bold white on red")
    try:
        shown = "~/" + folder.relative_to(Path.home()).as_posix()
    except ValueError:
        shown = str(folder)
    t = Text.assemble(("📂 ", ""), (title, "bold"), "  ", badge, "\n", (shown, "dim"))
    console.print(Panel(t, border_style="cyan", box=box.ROUNDED, expand=False))


def plan_table(moves: list[Move], root: Path, limit: int = 25) -> Table:
    """Table of planned moves (first ``limit`` rows)."""
    table = Table(box=box.SIMPLE_HEAVY, header_style="bold cyan", show_edge=False, pad_edge=False)
    table.add_column("File", overflow="fold", max_width=38)
    table.add_column("→ Destination", overflow="fold")
    table.add_column("Size", justify="right", style="dim")
    for m in moves[:limit]:
        try:
            rel = m.dst.relative_to(root).as_posix()
        except ValueError:
            rel = m.dst.as_posix()
        dest = Text(rel, style=style_for(m.category))
        if m.renamed:
            dest.append("  (renamed)", style="italic yellow")
        if m.duplicate_of is not None:
            dest.append(f"  copy of {m.duplicate_of.name}", style="italic bright_black")
        table.add_row(f"{ICONS.get(m.category, '📄')} {m.src.name}", dest, human_size(m.size))
    if len(moves) > limit:
        table.add_row(Text(f"… and {len(moves) - limit} more", style="dim italic"), "", "")
    return table


def summary_table(moves: list[Move]) -> Table:
    """Files and bytes per category with a little bar."""
    stats = summarize(moves)
    most = max((c for c, _ in stats.values()), default=1)
    table = Table(title="Summary", box=box.ROUNDED, header_style="bold", title_style="bold cyan")
    table.add_column("Category")
    table.add_column("Files", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("", min_width=20)
    for cat, (count, size) in stats.items():
        bar = "█" * max(1, round(count / most * 20))
        table.add_row(Text(f"{ICONS.get(cat, '📄')} {cat}", style=style_for(cat)), str(count),
                      human_size(size), Text(bar, style=style_for(cat)))
    total_files = sum(c for c, _ in stats.values())
    total_size = sum(s for _, s in stats.values())
    table.add_section()
    table.add_row(Text("Total", style="bold"), Text(str(total_files), style="bold"),
                  Text(human_size(total_size), style="bold"), "")
    return table


def destination_tree(moves: list[Move], root: Path) -> Tree:
    """Folder tree of where files will end up."""
    tree = Tree(Text(f"📁 {root.name or root}", style="bold"), guide_style="dim")
    counts: dict[tuple[str, ...], int] = {}
    top_category: dict[str, str] = {}
    for m in moves:
        try:
            parts = m.dst.parent.relative_to(root).parts
        except ValueError:
            parts = m.dst.parent.parts
        if parts:
            top_category.setdefault(parts[0], m.category)
        for i in range(1, len(parts) + 1):
            counts[parts[:i]] = counts.get(parts[:i], 0) + 1
    nodes: dict[tuple[str, ...], Tree] = {}
    for key in sorted(counts):
        parent = nodes.get(key[:-1], tree)
        label = Text(f"{key[-1]}/  ", style=style_for(top_category.get(key[0], "Other")))
        label.append(f"{counts[key]} file{'s' if counts[key] != 1 else ''}", style="dim")
        nodes[key] = parent.add(label)
    return tree


def duplicates_table(groups: list[list[Path]], root: Path) -> Table:
    table = Table(title="Duplicate files (same SHA-256)", box=box.ROUNDED, header_style="bold",
                  title_style="bold cyan")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Keep (oldest)", style="green")
    table.add_column("Duplicates", style="yellow")
    table.add_column("Wasted", justify="right")
    for i, group in enumerate(groups, 1):
        def rel(p: Path) -> str:
            try:
                return p.relative_to(root).as_posix()
            except ValueError:
                return str(p)
        wasted = group[0].stat().st_size * (len(group) - 1)
        table.add_row(str(i), rel(group[0]), "\n".join(rel(p) for p in group[1:]), human_size(wasted))
    return table

"""Command-line interface for envdrift."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich import box

from . import __version__
from .parser import EnvFile, parse_env_files
from .differ import compare_all
from .reporter import render_env_summary, render_all_reports, console as rep_console
from .advisor import stream_advice

console = Console()


def _resolve_sources(args: argparse.Namespace) -> dict[str, Path]:
    """Build label → Path mapping from CLI arguments."""
    sources: dict[str, Path] = {}

    # Positional env files: label=path or just path (label = stem)
    for raw in getattr(args, "envfiles", []):
        if "=" in raw:
            label, _, path_str = raw.partition("=")
        else:
            path_str = raw
            label = Path(path_str).stem
        sources[label] = Path(path_str).expanduser()

    # Auto-discover if no files given
    if not sources:
        cwd = Path(".")
        candidates = [".env", ".env.dev", ".env.development",
                      ".env.staging", ".env.prod", ".env.production",
                      ".env.test", ".env.local"]
        for name in candidates:
            p = cwd / name
            if p.exists():
                label = name.lstrip(".")  # ".env.staging" → "env.staging"
                sources[label] = p
        if not sources:
            console.print(
                "[yellow]No .env files found in current directory.[/yellow]\n"
                "  Pass files explicitly: [bold]envdrift dev=.env staging=.env.staging[/bold]"
            )
            sys.exit(0)

    return sources


async def _run_with_live(sources: dict[str, Path]) -> list[EnvFile]:
    """Parse env files concurrently with a live Rich progress table."""
    status: dict[str, str] = {label: "pending" for label in sources}

    def _build_table() -> Table:
        t = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan", pad_edge=False)
        t.add_column("Environment", style="cyan", no_wrap=True)
        t.add_column("File", style="dim")
        t.add_column("Status", no_wrap=True)
        for label, path in sources.items():
            s = status[label]
            if s == "pending":
                s_str = "[dim]waiting…[/dim]"
            elif s == "parsing":
                s_str = "[yellow]parsing…[/yellow]"
            elif s.startswith("ok:"):
                n = s.split(":")[1]
                s_str = f"[green]✓ {n} vars[/green]"
            else:
                s_str = f"[red]✗ {s}[/red]"
            t.add_row(label, str(path), s_str)
        return t

    results: dict[str, EnvFile] = {}

    async def _parse_one(label: str, path: Path) -> None:
        status[label] = "parsing"
        from .parser import parse_env_file
        ef = await parse_env_file(label, path)
        if ef.errors:
            status[label] = ef.errors[0]
        else:
            status[label] = f"ok:{len(ef.variables)}"
        results[label] = ef

    with Live(_build_table(), refresh_per_second=8, console=console) as live:
        async with asyncio.TaskGroup() as tg:
            for label, path in sources.items():
                tg.create_task(_parse_one(label, path))
                live.update(_build_table())
        live.update(_build_table())

    return [results[label] for label in sources if label in results]


def cmd_check(args: argparse.Namespace) -> None:
    """Run drift detection and display the results."""
    sources = _resolve_sources(args)

    if len(sources) < 2:
        console.print("[yellow]Need at least 2 environment files to compare.[/yellow]")
        sys.exit(1)

    env_files = asyncio.run(_run_with_live(sources))
    console.print()

    ref_label = getattr(args, "reference", None) or list(sources.keys())[0]

    render_env_summary(env_files)
    console.print()

    reports = compare_all(env_files, reference_label=ref_label)
    render_all_reports(reports)

    fmt = getattr(args, "format", None)
    if fmt == "json":
        output = []
        for r in reports:
            output.append({
                "reference": r.reference_label,
                "target": r.env_label,
                "missing": [e.key for e in r.missing],
                "extra": [e.key for e in r.extra],
                "changed": [e.key for e in r.changed],
            })
        print(json.dumps(output, indent=2))

    if getattr(args, "ai", False):
        console.print()
        stream_advice(reports)

    total = sum(r.total for r in reports)
    if total > 0:
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    """List all variables in a single .env file."""
    sources = _resolve_sources(args)
    env_files = asyncio.run(parse_env_files(sources))

    for ef in env_files:
        from rich.table import Table
        from rich.panel import Panel
        from rich import box as rbox

        t = Table(box=rbox.SIMPLE, show_header=True, header_style="bold cyan", pad_edge=False)
        t.add_column("Key", style="cyan", no_wrap=True)
        t.add_column("Value", style="dim")

        for key, val in sorted(ef.variables.items()):
            from .differ import _looks_like_secret
            display = f"{val[:4]}{'*' * min(len(val)-4, 8)}" if _looks_like_secret(key) and val else val
            t.add_row(key, display if not getattr(args, "secrets", False) else val)

        rep_console.print(Panel(t, title=f"{ef.label} ({len(ef.variables)} variables)", border_style="cyan"))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="envdrift",
        description="Detect environment variable drift across .env files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  envdrift                               # auto-discover .env files
  envdrift dev=.env staging=.env.staging prod=.env.prod
  envdrift dev=.env staging=.env.staging --ai
  envdrift dev=.env staging=.env.staging --format json
  envdrift list dev=.env
""",
    )
    parser.add_argument("--version", action="version", version=f"envdrift {__version__}")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # check (default command)
    p_check = sub.add_parser("check", help="Detect drift between environments (default)")
    p_check.add_argument("envfiles", nargs="*", metavar="LABEL=FILE",
                         help="Environment files to compare (e.g. dev=.env staging=.env.staging)")
    p_check.add_argument("--reference", "-r", metavar="LABEL",
                         help="Reference environment to compare against (default: first)")
    p_check.add_argument("--ai", action="store_true",
                         help="Stream AI remediation advice (requires ANTHROPIC_API_KEY)")
    p_check.add_argument("--format", "-f", choices=["table", "json"], default="table",
                         help="Output format (default: table)")
    p_check.set_defaults(func=cmd_check)

    # list
    p_list = sub.add_parser("list", help="List all variables in a .env file")
    p_list.add_argument("envfiles", nargs="*", metavar="LABEL=FILE",
                        help="File(s) to list")
    p_list.add_argument("--secrets", action="store_true",
                        help="Show secret values unmasked")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args(argv)

    # Default to 'check' if no subcommand given
    if not args.command:
        # Re-parse as check with all args as envfiles
        check_args = argparse.Namespace(
            command="check",
            envfiles=sys.argv[1:],
            reference=None,
            ai=False,
            format="table",
            func=cmd_check,
        )
        cmd_check(check_args)
        return

    args.func(args)


def entry_point() -> None:
    main()

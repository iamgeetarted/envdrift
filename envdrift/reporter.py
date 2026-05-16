"""Rich terminal output for envdrift."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .differ import DriftKind, DriftReport
from .parser import EnvFile

console = Console()


def _mask(value: str | None, is_secret: bool) -> str:
    if value is None:
        return "[dim]—[/dim]"
    if is_secret and value:
        return f"[dim]{value[:4]}{'*' * min(len(value) - 4, 8)}[/dim]"
    if len(value) > 60:
        return value[:57] + "..."
    return value


def render_env_summary(env_files: list[EnvFile]) -> None:
    """Show a summary table of all parsed environments."""
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("Environment", style="cyan")
    table.add_column("File", style="dim")
    table.add_column("Variables", justify="right")
    table.add_column("Errors", justify="right")

    for ef in env_files:
        err_str = f"[red]{len(ef.errors)}[/red]" if ef.errors else "[dim]0[/dim]"
        table.add_row(ef.label, str(ef.path), str(len(ef.variables)), err_str)

    console.print(Panel(table, title="Environments", border_style="cyan", box=box.ROUNDED))


def render_drift_report(report: DriftReport) -> None:
    """Render a drift report between two environments."""
    if report.is_clean:
        console.print(
            f"[green]✓ {report.env_label}[/green]  [dim]matches {report.reference_label} — no drift[/dim]"
        )
        return

    title = f"Drift: {report.reference_label} → {report.env_label}  ({report.total} issues)"
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold", border_style="dim")
    table.add_column("Kind", width=10, no_wrap=True)
    table.add_column("Key", style="bold white", no_wrap=True)
    table.add_column(f"in {report.reference_label}", style="dim")
    table.add_column(f"in {report.env_label}", style="dim")

    for entry in report.missing:
        table.add_row(
            "[red]MISSING[/red]", entry.key,
            _mask(entry.reference_value, entry.is_secret), "[dim]not set[/dim]"
        )

    for entry in report.extra:
        table.add_row(
            "[yellow]EXTRA[/yellow]", entry.key,
            "[dim]not set[/dim]", _mask(entry.actual_value, entry.is_secret)
        )

    for entry in report.changed:
        table.add_row(
            "[blue]CHANGED[/blue]", entry.key,
            _mask(entry.reference_value, entry.is_secret),
            _mask(entry.actual_value, entry.is_secret),
        )

    console.print(Panel(table, title=title, border_style="yellow", box=box.ROUNDED))


def render_all_reports(reports: list[DriftReport]) -> None:
    for report in reports:
        render_drift_report(report)

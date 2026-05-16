"""AI-powered remediation advice for environment drift."""

from __future__ import annotations

import os

from rich import box
from rich.console import Console
from rich.panel import Panel

from .differ import DriftReport

console = Console()


def _build_prompt(reports: list[DriftReport]) -> str:
    lines = []
    for report in reports:
        lines.append(f"\n## {report.reference_label} → {report.env_label}")
        if report.missing:
            lines.append(f"Missing ({len(report.missing)}): " + ", ".join(e.key for e in report.missing))
        if report.extra:
            lines.append(f"Extra ({len(report.extra)}): " + ", ".join(e.key for e in report.extra))
        if report.changed:
            lines.append(f"Changed ({len(report.changed)}): " + ", ".join(e.key for e in report.changed))

    drift_summary = "\n".join(lines) or "No drift detected."

    return (
        "I've compared environment variable files across environments and found this drift:\n\n"
        f"{drift_summary}\n\n"
        "Please provide concise remediation advice covering:\n"
        "1. Which missing variables are likely critical vs optional\n"
        "2. Whether any 'extra' variables could be security risks\n"
        "3. One concrete action to resolve the most important drift\n\n"
        "Be specific, practical, and developer-focused. Use markdown bullet points."
    )


def stream_advice(reports: list[DriftReport]) -> None:
    """Stream AI remediation advice for the drift reports."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print(
            "[red]ANTHROPIC_API_KEY not set.[/red]\n"
            "  Export it: [bold]export ANTHROPIC_API_KEY=your-key[/bold]"
        )
        return

    try:
        import anthropic
    except ImportError:
        console.print("[red]Install anthropic: pip install anthropic[/red]")
        return

    total_issues = sum(r.total for r in reports)
    if total_issues == 0:
        console.print("[dim]No drift to analyse.[/dim]")
        return

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(reports)

    console.print(Panel("[bold cyan]AI Remediation Advice[/bold cyan]", box=box.ROUNDED, border_style="cyan"))
    console.print()

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print("\n")

"""File-change polling watcher for continuous drift detection."""

from __future__ import annotations

import asyncio
import hashlib
import time
from pathlib import Path


async def _hash_file(path: Path) -> str:
    """Return a stable hash of *path*'s contents, or empty string if unreadable."""
    try:
        data = await asyncio.to_thread(path.read_bytes)
        return hashlib.md5(data).hexdigest()
    except OSError:
        return ""


async def watch_and_rerun(
    sources: dict[str, Path],
    interval: float,
    run_fn,
) -> None:
    """Poll *sources* every *interval* seconds and call *run_fn* when any file changes.

    Args:
        sources: Label → Path mapping of files to watch.
        interval: Poll interval in seconds.
        run_fn: Async callable with no arguments; called once on startup and
                again each time a change is detected.
    """
    from rich.console import Console
    from rich.rule import Rule

    console = Console()

    prev_hashes = {label: await _hash_file(path) for label, path in sources.items()}

    # Initial run
    await run_fn()

    while True:
        await asyncio.sleep(interval)

        new_hashes = {label: await _hash_file(path) for label, path in sources.items()}
        changed = [
            label for label, h in new_hashes.items()
            if h != prev_hashes.get(label, "")
        ]

        if changed:
            prev_hashes = new_hashes
            ts = time.strftime("%H:%M:%S")
            console.print()
            console.print(
                Rule(
                    f"[yellow]Changed: {', '.join(changed)}[/yellow]  "
                    f"[dim]{ts}[/dim]  "
                    "[dim]re-running…[/dim]",
                    style="yellow",
                )
            )
            console.print()
            await run_fn()
        else:
            ts = time.strftime("%H:%M:%S")
            console.print(
                f"  [dim]watching… (last checked {ts}, interval={interval:.0f}s)[/dim]",
                end="\r",
            )

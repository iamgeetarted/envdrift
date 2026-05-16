"""Async .env file parser."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import NamedTuple


class EnvFile(NamedTuple):
    label: str
    path: Path
    variables: dict[str, str]
    errors: list[str]


_LINE_RE = re.compile(r"""
    ^\s*
    (?:export\s+)?          # optional 'export'
    (?P<key>[A-Za-z_][A-Za-z0-9_]*)
    \s*=\s*
    (?P<value>
        "(?:[^"\\]|\\.)*"   # double-quoted
      | '(?:[^'\\]|\\.)*'   # single-quoted
      | [^\#\r\n]*          # unquoted (escape # so VERBOSE mode doesn't treat it as a comment)
    )
    \s*(?:\#.*)?$
""", re.VERBOSE)


def _unquote(v: str) -> str:
    v = v.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


async def parse_env_file(label: str, path: Path) -> EnvFile:
    """Read and parse a .env file asynchronously."""
    errors: list[str] = []
    variables: dict[str, str] = {}

    try:
        text = await asyncio.to_thread(path.read_text, encoding="utf-8", errors="replace")
    except OSError as e:
        errors.append(str(e))
        return EnvFile(label=label, path=path, variables={}, errors=errors)

    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _LINE_RE.match(line)
        if m:
            variables[m.group("key")] = _unquote(m.group("value"))
        else:
            errors.append(f"line {lineno}: could not parse: {line!r}")

    return EnvFile(label=label, path=path, variables=variables, errors=errors)


async def parse_env_files(sources: dict[str, Path]) -> list[EnvFile]:
    """Parse multiple .env files concurrently."""
    results: list[EnvFile] = []
    async with asyncio.TaskGroup() as tg:
        tasks = {
            label: tg.create_task(parse_env_file(label, path))
            for label, path in sources.items()
        }
    for label in sources:
        results.append(tasks[label].result())
    return results

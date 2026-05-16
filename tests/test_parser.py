"""Tests for envdrift.parser."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from envdrift.parser import parse_env_file, parse_env_files


def _write_env(content: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False)
    tmp.write(content)
    tmp.flush()
    return Path(tmp.name)


def test_parse_basic_vars():
    path = _write_env("DB_HOST=localhost\nDB_PORT=5432\n")
    ef = asyncio.run(parse_env_file("dev", path))
    assert ef.variables["DB_HOST"] == "localhost"
    assert ef.variables["DB_PORT"] == "5432"
    assert not ef.errors


def test_parse_quoted_values():
    path = _write_env('SECRET_KEY="my super secret"\nAPP_NAME=\'MyApp\'\n')
    ef = asyncio.run(parse_env_file("dev", path))
    assert ef.variables["SECRET_KEY"] == "my super secret"
    assert ef.variables["APP_NAME"] == "MyApp"


def test_parse_skips_comments_and_blanks():
    path = _write_env("# This is a comment\n\nDB_HOST=localhost\n")
    ef = asyncio.run(parse_env_file("dev", path))
    assert list(ef.variables.keys()) == ["DB_HOST"]


def test_parse_export_prefix():
    path = _write_env("export DB_HOST=localhost\n")
    ef = asyncio.run(parse_env_file("dev", path))
    assert ef.variables["DB_HOST"] == "localhost"


def test_missing_file_returns_error():
    ef = asyncio.run(parse_env_file("dev", Path("/nonexistent/.env")))
    assert ef.variables == {}
    assert len(ef.errors) == 1


def test_parse_multiple_concurrent():
    path_a = _write_env("A=1\nB=2\n")
    path_b = _write_env("A=1\nC=3\n")
    results = asyncio.run(parse_env_files({"dev": path_a, "prod": path_b}))
    assert len(results) == 2
    labels = {ef.label for ef in results}
    assert labels == {"dev", "prod"}

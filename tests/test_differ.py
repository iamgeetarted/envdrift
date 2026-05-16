"""Tests for envdrift.differ."""

from pathlib import Path

import pytest

from envdrift.differ import compare, compare_all, DriftKind
from envdrift.parser import EnvFile


def _ef(label: str, vars: dict) -> EnvFile:
    return EnvFile(label=label, path=Path(f".env.{label}"), variables=vars, errors=[])


def test_no_drift():
    ref = _ef("dev", {"DB_HOST": "localhost", "PORT": "5432"})
    tgt = _ef("prod", {"DB_HOST": "db.example.com", "PORT": "5432"})
    # PORT is same, DB_HOST changed
    report = compare(ref, tgt)
    assert report.total == 1
    assert len(report.changed) == 1
    assert report.changed[0].key == "DB_HOST"


def test_missing_key():
    ref = _ef("dev", {"DB_HOST": "localhost", "REDIS_URL": "redis://localhost"})
    tgt = _ef("prod", {"DB_HOST": "db.example.com"})
    report = compare(ref, tgt)
    assert len(report.missing) == 1
    assert report.missing[0].key == "REDIS_URL"
    assert report.missing[0].kind == DriftKind.MISSING


def test_extra_key():
    ref = _ef("dev", {"DB_HOST": "localhost"})
    tgt = _ef("prod", {"DB_HOST": "db.example.com", "NEW_FEATURE_FLAG": "true"})
    report = compare(ref, tgt)
    assert len(report.extra) == 1
    assert report.extra[0].key == "NEW_FEATURE_FLAG"


def test_is_clean_when_identical():
    ref = _ef("dev", {"X": "1", "Y": "2"})
    tgt = _ef("prod", {"X": "1", "Y": "2"})
    report = compare(ref, tgt)
    assert report.is_clean


def test_compare_all_uses_first_as_reference():
    dev = _ef("dev", {"A": "1", "B": "2"})
    staging = _ef("staging", {"A": "1"})
    prod = _ef("prod", {"A": "1", "B": "2", "C": "3"})
    reports = compare_all([dev, staging, prod])
    assert len(reports) == 2
    labels = {r.env_label for r in reports}
    assert labels == {"staging", "prod"}


def test_secret_key_detection():
    ref = _ef("dev", {"SECRET_KEY": "dev-secret", "DB_HOST": "localhost"})
    tgt = _ef("prod", {"SECRET_KEY": "prod-secret", "DB_HOST": "db.prod"})
    report = compare(ref, tgt)
    secret_entry = next(e for e in report.changed if e.key == "SECRET_KEY")
    assert secret_entry.is_secret

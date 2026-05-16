"""Detect drift between environment variable sets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from .parser import EnvFile


class DriftKind(str, Enum):
    MISSING = "missing"      # key exists in reference but not here
    EXTRA = "extra"          # key exists here but not in reference
    CHANGED = "changed"      # key exists in both but value differs
    SECRET_EXPOSED = "secret_exposed"  # value looks like a secret and differs


_SECRET_KEYS = re.compile(
    r"(secret|password|passwd|token|key|auth|credential|private|cert|api_key)",
    re.IGNORECASE,
)


def _looks_like_secret(key: str) -> bool:
    return bool(_SECRET_KEYS.search(key))


@dataclass
class DriftEntry:
    key: str
    kind: DriftKind
    env_label: str
    reference_label: str
    reference_value: str | None = None
    actual_value: str | None = None
    is_secret: bool = False


@dataclass
class DriftReport:
    reference_label: str
    env_label: str
    missing: list[DriftEntry] = field(default_factory=list)
    extra: list[DriftEntry] = field(default_factory=list)
    changed: list[DriftEntry] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.missing) + len(self.extra) + len(self.changed)

    @property
    def is_clean(self) -> bool:
        return self.total == 0


def compare(reference: EnvFile, target: EnvFile) -> DriftReport:
    """Compare *target* against *reference*, returning a DriftReport."""
    report = DriftReport(reference_label=reference.label, env_label=target.label)
    ref_keys = set(reference.variables)
    tgt_keys = set(target.variables)

    for key in sorted(ref_keys - tgt_keys):
        report.missing.append(DriftEntry(
            key=key,
            kind=DriftKind.MISSING,
            env_label=target.label,
            reference_label=reference.label,
            reference_value=reference.variables[key],
            is_secret=_looks_like_secret(key),
        ))

    for key in sorted(tgt_keys - ref_keys):
        report.extra.append(DriftEntry(
            key=key,
            kind=DriftKind.EXTRA,
            env_label=target.label,
            reference_label=reference.label,
            actual_value=target.variables[key],
            is_secret=_looks_like_secret(key),
        ))

    for key in sorted(ref_keys & tgt_keys):
        if reference.variables[key] != target.variables[key]:
            report.changed.append(DriftEntry(
                key=key,
                kind=DriftKind.CHANGED,
                env_label=target.label,
                reference_label=reference.label,
                reference_value=reference.variables[key],
                actual_value=target.variables[key],
                is_secret=_looks_like_secret(key),
            ))

    return report


def compare_all(env_files: Sequence[EnvFile], reference_label: str | None = None) -> list[DriftReport]:
    """Compare all environments against the reference (first by default)."""
    if not env_files:
        return []
    ref_label = reference_label or env_files[0].label
    reference = next((f for f in env_files if f.label == ref_label), env_files[0])
    return [compare(reference, target) for target in env_files if target.label != ref_label]

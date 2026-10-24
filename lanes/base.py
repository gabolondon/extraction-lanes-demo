"""Shared row type and the one lane interface: ``extract(doc_path) -> list[Row]``."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    page: int  # 1-based
    printed_label: str
    value: str
    unit: str
    min: str
    max: str
    verbatim: str = ""


class LaneError(RuntimeError):
    """A lane could not produce a trustworthy answer (never reported as zero rows)."""


class TruncatedAnswer(LaneError):
    """The model stopped because it hit the length limit; the JSON cannot be trusted."""

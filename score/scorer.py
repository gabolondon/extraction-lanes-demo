"""Score a lane's rows against the gold CSV."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from lanes.base import Row

_INVISIBLE = dict.fromkeys(map(ord, "­​‌‍⁠﻿"), None)


def norm_name(s: str) -> str:
    """Space- and invisible-character-insensitive, case-insensitive."""
    return "".join(s.translate(_INVISIBLE).split()).casefold()


def norm_num(s: str) -> str:
    s = s.strip().replace(",", ".")
    try:
        return f"{float(s):.6g}"
    except ValueError:
        return s.casefold()


def norm_unit(s: str) -> str:
    return "".join(s.split()).casefold()


def load_gold(path: str | Path) -> list[Row]:
    with Path(path).open(encoding="utf-8", newline="") as fh:
        return [
            Row(int(r["page"]), r["printed_label"], r["value"], r["unit"], r["min"], r["max"])
            for r in csv.DictReader(fh)
        ]


def _pr_key(r: Row):
    return (norm_name(r.printed_label), norm_num(r.value))


def _strict_key(r: Row):
    return (*_pr_key(r), norm_unit(r.unit), norm_num(r.min), norm_num(r.max))


@dataclass
class Score:
    n_gold: int
    n_pred: int
    strict: float  # strict matches / gold rows
    precision: float  # name+value
    recall: float  # name+value
    phantom: int  # predicted rows whose name is not a gold name
    zero_row_pages: int  # pages with gold rows where the lane returned none
    seconds_per_page: float


def score(pred: list[Row], gold: list[Row], n_pages: int, seconds: float) -> Score:
    pr_hits = sum((Counter(map(_pr_key, pred)) & Counter(map(_pr_key, gold))).values())
    strict_hits = sum((Counter(map(_strict_key, pred)) & Counter(map(_strict_key, gold))).values())
    gold_names = {norm_name(g.printed_label) for g in gold}
    gold_pages = {g.page for g in gold}
    pred_pages = {p.page for p in pred}
    return Score(
        n_gold=len(gold),
        n_pred=len(pred),
        strict=strict_hits / len(gold) if gold else 0.0,
        precision=pr_hits / len(pred) if pred else 0.0,
        recall=pr_hits / len(gold) if gold else 0.0,
        phantom=sum(norm_name(p.printed_label) not in gold_names for p in pred),
        zero_row_pages=len(gold_pages - pred_pages),
        seconds_per_page=seconds / n_pages if n_pages else 0.0,
    )

"""Layout lane: deterministic, no model. PyMuPDF word boxes -> lines -> rows.

It assumes one printed line is one row: ``name  value  unit  min  max``. That assumption is the
point of the example: it is fast and exact on clean tables and it fails on stacked layouts.
"""

from __future__ import annotations

import re

import pymupdf

from lanes.base import Row

_NUM = re.compile(r"^[-+]?\d+(?:\.\d+)?$")
Y_TOL = 2.5


def _bucket_lines(words: list[tuple]) -> list[list[tuple]]:
    """Group word boxes whose vertical centres are within Y_TOL; each line sorted left to right."""
    lines: list[tuple[float, list[tuple]]] = []
    for w in sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0])):
        yc = (w[1] + w[3]) / 2
        if lines and abs(lines[-1][0] - yc) <= Y_TOL:
            lines[-1][1].append(w)
        else:
            lines.append((yc, [w]))
    return [sorted(ws, key=lambda w: w[0]) for _, ws in lines]


def _row_from_tokens(page_no: int, toks: list[str]) -> Row | None:
    if len(toks) < 5:
        return None
    name, (value, unit, lo, hi) = " ".join(toks[:-4]), toks[-4:]
    if not (_NUM.match(value) and _NUM.match(lo) and _NUM.match(hi)) or _NUM.match(unit):
        return None
    return Row(page_no, name, value, unit, lo, hi, " ".join(toks))


def extract(doc_path: str) -> list[Row]:
    rows: list[Row] = []
    with pymupdf.open(doc_path) as doc:
        for page in doc:
            for line in _bucket_lines(page.get_text("words")):
                row = _row_from_tokens(page.number + 1, [w[4] for w in line])
                if row:
                    rows.append(row)
    return rows

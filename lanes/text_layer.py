"""Flag pages whose text layer cannot be trusted, so a bench can say so instead of blaming a lane."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pymupdf

INVISIBLE = "­​‌‍⁠﻿"
_NUMBERISH = re.compile(r"^[-+]?[\d.,]+%?$")


@dataclass
class TextLayerReport:
    broken: bool
    reasons: list[str] = field(default_factory=list)


def _garbled(tok: str) -> bool:
    if any(c == "�" or "" <= c <= "" for c in tok):
        return True
    if _NUMBERISH.match(tok) or len(tok) < 3:
        return False
    letters = sum(c.isalpha() for c in tok)
    return letters / len(tok) < 0.5 and not any(c.isdigit() for c in tok)


def check_text(text: str) -> TextLayerReport:
    reasons = []
    found = sorted({f"U+{ord(c):04X}" for c in text if c in INVISIBLE})
    if found:
        reasons.append("invisible characters inside the text layer: " + ", ".join(found))
    toks = text.split()
    if len(toks) >= 5 and sum(_garbled(t) for t in toks) / len(toks) > 0.5:
        reasons.append("mostly non-word tokens")
    return TextLayerReport(bool(reasons), reasons)


def check_pdf(doc_path: str) -> list[TextLayerReport]:
    with pymupdf.open(doc_path) as doc:
        return [check_text(p.get_text()) for p in doc]

"""Redaction gate, fail-closed: detect -> redact -> render -> verify. Any doubt is a BLOCK."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from gate.detect import Span, detect

DPI = 200


class SpanNotFound(RuntimeError):
    """A detected span could not be located on the page, so it could not be removed."""


@dataclass
class GateResult:
    verdict: str  # PASS | BLOCK
    reason: str = ""
    spans: list[Span] = field(default_factory=list)
    png_path: Path | None = None
    redacted_text: str = ""


def redact_page(page: pymupdf.Page, spans: list[Span]) -> None:
    for s in spans:
        rects = page.search_for(s.text)
        if not rects:
            raise SpanNotFound(f"cannot locate {s.kind} span on the page")
        for r in rects:
            page.add_redact_annot(r, fill=(0, 0, 0))
    page.apply_redactions()  # removes the text itself, not just paints over it


def run_gate(pdf_path: str | Path, page_no: int, out_dir: str | Path, verifier,
             detector: Callable[[str], list[Span]] = detect) -> GateResult:
    """page_no is 1-based. The PNG exists only if the verdict is PASS."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    png_path = out_dir / f"{Path(pdf_path).stem}_p{page_no}.png"
    png_path.unlink(missing_ok=True)
    result = GateResult("BLOCK", "not finished")
    try:
        with pymupdf.open(pdf_path) as doc:
            page = doc[page_no - 1]
            spans = detector(page.get_text())
            result.spans = spans
            redact_page(page, spans)
            result.redacted_text = page.get_text()
            png = page.get_pixmap(dpi=DPI).tobytes("png")
        png_path.write_bytes(png)
        answer = verifier.verify(png, result.redacted_text)
        if not isinstance(answer, str) or answer.strip().upper() != "PASS":
            result.reason = f"verifier answered {answer!r}"
        else:
            result.verdict, result.reason, result.png_path = "PASS", "verifier PASS", png_path
    except Exception as exc:  # fail closed: any doubt blocks
        result.reason = f"{type(exc).__name__}: {exc}"
    finally:
        if result.verdict != "PASS":
            png_path.unlink(missing_ok=True)
            result.png_path = None
    return result

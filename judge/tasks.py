"""The two example tasks."""

from __future__ import annotations

import csv
from pathlib import Path

from catalog.data import BY_CODE, NONE_OF_THESE
from catalog.matcher import FixedMatcher, normalize
from judge.core import Request, Task

SKIP = "skip"
_MATCHER = FixedMatcher()


def _field_mapping_request(item: dict) -> Request:
    codes = _MATCHER.shortlist(item["printed_label"], k=5)  # the shortlist is built by code
    return Request(
        facts={"printed name": item["printed_label"], "unit": item["unit"],
               "limits": f"{item['min']} .. {item['max']}", "language": item["lang"]},
        question="Which catalog code does this printed parameter name map to?",
        choices=[*codes, NONE_OF_THESE],
        describe={c: " / ".join(BY_CODE[c].aliases) for c in codes},
    )


# field_mapping sends only printed parameter names and numbers: public class.
FIELD_MAPPING = Task("field_mapping", "public", _field_mapping_request,
                     lambda item, req: item["code"], abstain=(NONE_OF_THESE,))


def _attribution_request(item: dict) -> Request:
    # facts are raw page text, which can carry a header with personal data: personal class.
    return Request(
        facts={"page text": "\n".join(item["lines"])},
        question=f"Which printed name does the value {item['value']} {item['unit']} belong to? "
                 f"Answer {SKIP} if it belongs to none of them.",
        choices=[*item["candidates"], SKIP],
    )


LINE_ATTRIBUTION = Task("line_attribution", "personal", _attribution_request,
                        lambda item, req: item["truth"], abstain=(SKIP,))
TASKS = {t.name: t for t in (FIELD_MAPPING, LINE_ATTRIBUTION)}


# ---- cases ----------------------------------------------------------------------------------
def field_mapping_cases(corpus: Path) -> list[dict]:
    with (corpus / "gold" / "matcher_cases.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def attribution_cases(corpus: Path, window: int = 4) -> list[dict]:
    """Value lines of the stacked certificate (owner = the name above) plus a few that own nothing."""
    import pymupdf

    from score.scorer import load_gold, norm_name

    cases: list[dict] = []
    gold = load_gold(corpus / "gold" / "cert_es_stacked.csv")
    names = {norm_name(g.printed_label) for g in gold}
    with pymupdf.open(corpus / "pdfs" / "cert_es_stacked.pdf") as doc:
        for g in gold:
            page_lines = [ln.translate(dict.fromkeys(map(ord, "\u00ad\u200b\u200c"), None))
                          for ln in doc[g.page - 1].get_text().splitlines()]
            idx = next(i for i, ln in enumerate(page_lines) if norm_name(ln) == norm_name(g.printed_label))
            lo, hi = max(0, idx - window), idx + window + 1
            lines = page_lines[lo:hi]
            cands = [ln for ln in lines if norm_name(ln) in names]
            cases.append(dict(lines=lines, value=g.value, unit=g.unit, candidates=cands,
                              truth=next(c for c in cands if norm_name(c) == norm_name(g.printed_label))))
    # numbers that belong to no printed name
    with pymupdf.open(corpus / "pdfs" / "cert_en_wrapped.pdf") as doc:
        notes = [ln for ln in doc[1].get_text().splitlines() if ln.strip()]
    wrapped = load_gold(corpus / "gold" / "cert_en_wrapped.csv")
    for k, ln in enumerate(notes):
        if any(ch.isdigit() for ch in ln):
            digits = "".join(ch for ch in ln if ch.isdigit())
            cases.append(dict(lines=notes, value=digits[:1] or "0", unit="", truth=SKIP,
                              candidates=[w.printed_label for w in wrapped[k:k + 3]]))
    return cases


def describe_filler() -> str:
    return " ".join(sorted(normalize(w) for w in _MATCHER.filler))

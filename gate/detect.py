"""Detector: regex patterns plus a small keyword list for header fields, and a keep-list."""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"\+\d{1,3}(?:[ .-]?\d{2,4}){2,4}")
CERT_NO = re.compile(r"\b[A-Z]{2,4}-\d{4}-\d{4,6}\b")

# header labels whose value is personal data (English and Spanish)
LABELS = ("technician", "customer contact", "site address",
          "técnico", "contacto del cliente", "dirección del sitio")
ADDRESS_LABELS = ("site address", "dirección del sitio")

# keep-list: fields and measurement lines that must never be redacted
KEEP_LABELS = ("calibration date", "fecha de calibración", "instrument model",
               "modelo del instrumento")
KEEP_UNITS = {"bar", "°c", "l/min", "%", "%rh", "mohm", "ohm", "v", "ma", "mv", "s", "ml/min",
              "m", "min", "%/k", "id"}
_NUM = re.compile(r"^[-+]?\d+(?:\.\d+)?$")


@dataclass(frozen=True)
class Span:
    text: str
    kind: str  # label | email | phone | cert_no | address_line


def _is_measurement_line(line: str) -> bool:
    toks = line.split()
    return sum(bool(_NUM.match(t)) for t in toks) >= 3 and any(
        t.casefold() in KEEP_UNITS for t in toks
    )


def _is_keep(line: str) -> bool:
    low = line.strip().casefold()
    return low.startswith(KEEP_LABELS) or _is_measurement_line(line)


def detect(text: str) -> list[Span]:
    spans: dict[str, Span] = {}
    lines = text.splitlines()
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line or _is_keep(line):
            continue
        low = line.casefold()
        if low.startswith(LABELS) and ":" in line:
            value = line.split(":", 1)[1].strip()
            if value:
                spans.setdefault(value, Span(value, "label"))
            if low.startswith(ADDRESS_LABELS):
                nxt = next((ln.strip() for ln in lines[i + 1:] if ln.strip()), "")
                if nxt and not _is_keep(nxt) and ":" not in nxt:
                    spans.setdefault(nxt, Span(nxt, "address_line"))
        for kind, pat in (("email", EMAIL), ("phone", PHONE), ("cert_no", CERT_NO)):
            for m in pat.finditer(line):
                spans.setdefault(m.group(0), Span(m.group(0), kind))
    return list(spans.values())

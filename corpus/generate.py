"""Deterministic example corpus: three certificates, gold CSVs, a PII fixture.

Gold is known by construction: the rows are generated first and drawn second.
Run: ``python -m corpus.generate [out_dir]``  (default: ./corpus)
"""

from __future__ import annotations

import csv
import random
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from corpus.names import RowSpec, build_rows
from corpus.pii_fixture import build as build_fixture

SEED = 20260101
W, H = 595, 842
FIELDS = ["page", "printed_label", "value", "unit", "min", "max"]
ZW = ("\x01", "\x02", "\x03")  # drawn as nothing; extracted as ZWSP, soft hyphen, ZWNJ


@dataclass
class Identity:
    lab: str
    tech: str
    contact: str
    phone: str
    email: str
    cert: str
    street: str
    city: str
    date: str
    model: str


EN_ID = Identity(
    "Northwind Metrology", "Elena Marrow", "Jonas Hartwell", "+44 20 7946 0183",
    "j.hartwell@example.org", "NW-2026-004217", "14 Harbour Lane", "Port Verity, PV4 2QT",
    "2026-03-14", "PG-200",
)
EN_ID2 = Identity(
    "Northwind Metrology", "Anil Deverell", "Margot Linden", "+44 20 7946 0291",
    "m.linden@example.org", "NW-2026-005530", "3 Millrace Court", "Port Verity, PV1 7AB",
    "2026-04-02", "FM-85",
)
ES_ID = Identity(
    "Laboratorio Andino de Calibración", "Camila Ortúzar", "Rodrigo Valcárcel",
    "+57 601 555 0142", "r.valcarcel@example.org", "LAC-2026-001873", "Calle de los Ceibos 220",
    "Villa Alta, 110231", "2026-02-20", "TT-120",
)
LABELS = {
    "en": ["Certificate No", "Technician", "Customer contact", "Phone", "Email", "Site address",
           "Calibration date", "Instrument model"],
    "es": ["Certificado n.º", "Técnico", "Contacto del cliente", "Teléfono", "Correo",
           "Dirección del sitio", "Fecha de calibración", "Modelo del instrumento"],
}


# ---- font trick for the stacked certificate -------------------------------------------------
def _patch_font(doc: pymupdf.Document, page: pymupdf.Page, tu_xref: int) -> None:
    """Make codes 1..3 draw nothing (zero width) but extract as ZWSP / soft hyphen / ZWNJ."""
    xref = page.insert_font(fontname="helv")
    f = pymupdf.Font("helv")
    widths = " ".join("0" if c < 32 else str(round(f.glyph_advance(c) * 1000)) for c in range(256))
    doc.update_object(
        xref,
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        "/Encoding << /Type /Encoding /BaseEncoding /WinAnsiEncoding "
        "/Differences [1 /space 2 /space 3 /space] >> "
        f"/FirstChar 0 /LastChar 255 /Widths [{widths}] /ToUnicode {tu_xref} 0 R >>",
    )


def _tounicode(doc: pymupdf.Document) -> int:
    xref = doc.get_new_xref()
    body = "\n".join(f"<{c:02X}> <{c:04X}>" for c in range(32, 256))
    cmap = (
        "/CIDInit /ProcSet findresource begin 12 dict begin begincmap "
        "/CMapName /Adobe-Identity-UCS def /CMapType 2 def\n"
        "1 begincodespacerange <00> <FF> endcodespacerange\n"
        "3 beginbfchar\n<01> <200B>\n<02> <00AD>\n<03> <200C>\nendbfchar\n"
        f"224 beginbfchar\n{body}\nendbfchar\n"
        "endcmap CMapName currentdict /CMap defineresource pop end end"
    )
    doc.update_object(xref, f"<< /Length {len(cmap)} >>")
    doc.update_stream(xref, cmap.encode())
    return xref


def _pollute(rng: random.Random, name: str) -> str:
    """Insert invisible characters inside words (never at word edges)."""
    out = []
    for word in name.split(" "):
        if len(word) > 5:
            for _ in range(rng.choice([1, 2])):
                i = rng.randrange(2, len(word) - 1)
                word = word[:i] + rng.choice(ZW) + word[i:]
        out.append(word)
    return " ".join(out)


# ---- drawing --------------------------------------------------------------------------------
def _fmt(x: float, dec: int) -> str:
    return f"{x:.{dec}f}"


def _numbers(rng: random.Random, r: RowSpec) -> tuple[str, str, str, str]:
    dec = 3 if (r.hi - r.lo) < 0.1 else 2
    value = r.lo + (r.hi - r.lo) * rng.uniform(0.2, 0.8)
    return _fmt(value, dec), r.unit, _fmt(r.lo, dec), _fmt(r.hi, dec)


def _header(page: pymupdf.Page, ident: Identity, lang: str) -> float:
    y = 56
    title = "Calibration Certificate" if lang == "en" else "Certificado de calibración"
    page.insert_text((50, y), f"{ident.lab} - {title}", fontsize=13)
    lab = LABELS[lang]
    values = [ident.cert, ident.tech, ident.contact, ident.phone, ident.email, ident.street]
    for label, val in zip(lab[:6], values, strict=True):
        y += 18
        page.insert_text((50, y), f"{label}: {val}", fontsize=10)
    y += 16
    page.insert_text((50, y), f"    {ident.city}", fontsize=10)
    for label, val in zip(lab[6:], (ident.date, ident.model), strict=True):
        y += 18
        page.insert_text((50, y), f"{label}: {val}", fontsize=10)
    return y + 34


def _footer(page: pymupdf.Page, n: int, total: int, lang: str) -> None:
    word = "Page" if lang == "en" else "Página"
    of = "of" if lang == "en" else "de"
    page.insert_text((250, 826), f"{word} {n} {of} {total}", fontsize=8)


def _write_gold(path: Path, golds: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(golds)


def cert_en_clean(rng: random.Random, path: Path) -> list[dict]:
    per_page = [18, 26, 26, 16]
    specs = build_rows(rng, "en", sum(per_page))
    doc, golds, k = pymupdf.open(), [], 0
    for pno, n in enumerate(per_page, 1):
        page = doc.new_page(width=W, height=H)
        y = _header(page, EN_ID, "en") if pno == 1 else 60
        for x, t in zip((50, 300, 360, 420, 490),
                        ("Parameter", "Value", "Unit", "Tol. min", "Tol. max"), strict=True):
            page.insert_text((x, y), t, fontsize=9, fontname="hebo")
        y += 20
        for r in specs[k:k + n]:
            v, u, lo, hi = _numbers(rng, r)
            for x, t in zip((50, 300, 360, 420, 490), (r.name, v, u, lo, hi), strict=True):
                page.insert_text((x, y), t, fontsize=9)
            golds.append(dict(page=pno, printed_label=r.name, value=v, unit=u, min=lo, max=hi,
                              _code=r.code))
            y += 21
        k += n
        _footer(page, pno, len(per_page), "en")
    doc.save(str(path))
    return golds


def cert_es_stacked(rng: random.Random, path: Path) -> list[dict]:
    per_page = [9, 12, 12, 10]
    specs = build_rows(rng, "es", sum(per_page))
    doc, golds, k = pymupdf.open(), [], 0
    tu = _tounicode(doc)
    for pno, n in enumerate(per_page, 1):
        page = doc.new_page(width=W, height=H)
        _patch_font(doc, page, tu)
        y = _header(page, ES_ID, "es") if pno == 1 else 60
        for r in specs[k:k + n]:
            v, u, lo, hi = _numbers(rng, r)
            page.insert_text((50, y), _pollute(rng, r.name), fontsize=10)
            page.insert_text((70, y + 13), v, fontsize=10)
            page.insert_text((70, y + 26), u, fontsize=10)
            page.insert_text((70, y + 39), f"{lo}    {hi}", fontsize=10)
            golds.append(dict(page=pno, printed_label=r.name, value=v, unit=u, min=lo, max=hi,
                              _code=r.code))
            y += 56
        k += n
        _footer(page, pno, len(per_page), "es")
    doc.save(str(path))
    return golds


NOTES = [
    "Notes and conditions",
    "This certificate is issued for the instrument identified on page 1 only.",
    "Reference standards are traceable to the national standard of the issuing lab.",
    "Expanded uncertainty is stated at a coverage factor of k = 2.",
    "Results relate to the item as received and do not imply long-term stability.",
    "Tolerance limits are those of the instrument data sheet.",
    "Reproduction of this certificate is permitted only in full.",
]


def cert_en_wrapped(rng: random.Random, path: Path) -> list[dict]:
    doc, golds = pymupdf.open(), []
    specs = build_rows(rng, "en", 60, extra_tail=True)
    k = 0
    for pno in (1, 2, 3):
        page = doc.new_page(width=W, height=H)
        y = _header(page, EN_ID2, "en") if pno == 1 else 60
        if pno == 2:
            for i, ln in enumerate(NOTES):
                page.insert_text((50, y + 20 * i), ln, fontsize=10)
            _footer(page, pno, 3, "en")
            continue
        while True:
            r = specs[k]
            lines = textwrap.wrap(r.name, 30)
            if y + 11 * len(lines) > 800:
                break
            v, u, lo, hi = _numbers(rng, r)
            for i, ln in enumerate(lines):
                page.insert_text((50, y + 11 * i), ln, fontsize=9)
            for x, t in zip((390, 445, 485, 535), (v, u, lo, hi), strict=True):
                page.insert_text((x, y), t, fontsize=9)
            golds.append(dict(page=pno, printed_label=r.name, value=v, unit=u, min=lo, max=hi,
                              _code=r.code))
            y += 11 * len(lines) + 7
            k += 1
        _footer(page, pno, 3, "en")
    doc.save(str(path))
    return golds


DOCS = {
    "cert_en_clean": cert_en_clean,
    "cert_es_stacked": cert_es_stacked,
    "cert_en_wrapped": cert_en_wrapped,
}


def generate(out: Path) -> dict[str, list[dict]]:
    (out / "pdfs").mkdir(parents=True, exist_ok=True)
    (out / "gold").mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    result = {}
    for name, fn in DOCS.items():
        golds = fn(rng, out / "pdfs" / f"{name}.pdf")
        _write_gold(out / "gold" / f"{name}.csv", [{k: g[k] for k in FIELDS} for g in golds])
        result[name] = golds
    build_fixture(out / "pdfs" / "pii_fixture.pdf")
    # name -> code cases for the matcher and the judge
    seen, cases = set(), []
    for doc, golds in result.items():
        lang = "es" if "_es_" in doc else "en"
        for g in golds:
            if g["printed_label"] not in seen:
                seen.add(g["printed_label"])
                cases.append(dict(doc=doc, lang=lang, printed_label=g["printed_label"], unit=g["unit"],
                                  min=g["min"], max=g["max"], code=g["_code"]))
    with (out / "gold" / "matcher_cases.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["doc", "lang", "printed_label", "unit", "min", "max", "code"])
        w.writeheader()
        w.writerows(cases)
    return result


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    res = generate(target)
    for name, golds in res.items():
        print(f"{name}: {len(golds)} gold rows, pages {sorted({g['page'] for g in golds})}")
    print(f"pii_fixture: 1 page, 7 planted identifiers  ->  {target.name}/")

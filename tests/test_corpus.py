import csv

import pymupdf

from corpus.generate import generate
from corpus.pii_fixture import PLANTED
from lanes.text_layer import check_pdf


def test_three_certificates_and_gold(corpus):
    for name, pages in [("cert_en_clean", 4), ("cert_es_stacked", 4), ("cert_en_wrapped", 3)]:
        with pymupdf.open(corpus / "pdfs" / f"{name}.pdf") as d:
            assert len(d) == pages
        rows = list(csv.DictReader((corpus / "gold" / f"{name}.csv").open(encoding="utf-8")))
        assert len(rows) > 25
        assert list(rows[0]) == ["page", "printed_label", "value", "unit", "min", "max"]


def test_generation_is_deterministic(corpus, tmp_path):
    generate(tmp_path)
    for name in ("cert_en_clean", "cert_es_stacked", "cert_en_wrapped", "matcher_cases"):
        a = (corpus / "gold" / f"{name}.csv").read_text(encoding="utf-8")
        b = (tmp_path / "gold" / f"{name}.csv").read_text(encoding="utf-8")
        assert a == b


def test_stacked_text_layer_is_broken_but_gold_is_clean(corpus):
    reports = check_pdf(str(corpus / "pdfs" / "cert_es_stacked.pdf"))
    assert all(r.broken for r in reports)
    assert not any(r.broken for r in check_pdf(str(corpus / "pdfs" / "cert_en_clean.pdf")))
    gold = (corpus / "gold" / "cert_es_stacked.csv").read_text(encoding="utf-8")
    assert not any(c in gold for c in "­​‌\x01\x02\x03")


def test_wrapped_has_a_page_without_rows(corpus):
    rows = list(csv.DictReader((corpus / "gold" / "cert_en_wrapped.csv").open(encoding="utf-8")))
    assert {r["page"] for r in rows} == {"1", "3"}


def test_fixture_has_exactly_seven_planted_identifiers(corpus):
    assert len(PLANTED) == 7
    with pymupdf.open(corpus / "pdfs" / "pii_fixture.pdf") as d:
        text = d[0].get_text()
    assert all(p in text for p in PLANTED)

import json

import pytest

from lanes import layout, text_llm, vision
from lanes.backends import Completion, ConfigError, FakeBackend, line_parser_handler
from lanes.base import LaneError, TruncatedAnswer
from score import load_gold, score


def test_layout_is_exact_on_the_clean_certificate(corpus):
    pdf = corpus / "pdfs" / "cert_en_clean.pdf"
    gold = load_gold(corpus / "gold" / "cert_en_clean.csv")
    s = score(layout.extract(str(pdf)), gold, 4, 1.0)
    assert s.strict == 1.0 and s.phantom == 0 and s.zero_row_pages == 0


def test_layout_is_expected_to_fail_on_the_stacked_certificate(corpus):
    pdf = corpus / "pdfs" / "cert_es_stacked.pdf"
    gold = load_gold(corpus / "gold" / "cert_es_stacked.csv")
    rows = layout.extract(str(pdf))
    s = score(rows, gold, 4, 1.0)
    assert s.strict == 0.0 and s.zero_row_pages == 4


def test_layout_misses_wrapped_names(corpus):
    pdf = corpus / "pdfs" / "cert_en_wrapped.pdf"
    gold = load_gold(corpus / "gold" / "cert_en_wrapped.csv")
    s = score(layout.extract(str(pdf)), gold, 3, 1.0)
    assert s.strict < 0.2


def test_text_lane_with_fake_backend(corpus):
    pdf = corpus / "pdfs" / "cert_en_clean.pdf"
    rows = text_llm.extract(str(pdf), FakeBackend(line_parser_handler))
    assert len(rows) == len(load_gold(corpus / "gold" / "cert_en_clean.csv"))


def test_truncated_answer_is_an_error_not_an_empty_page(corpus):
    pdf = corpus / "pdfs" / "cert_en_clean.pdf"
    backend = FakeBackend(lambda p, i: Completion('{"rows": []}', truncated=True))
    with pytest.raises(TruncatedAnswer):
        text_llm.extract(str(pdf), backend)


def test_unparseable_answer_is_an_error(corpus):
    backend = FakeBackend(lambda p, i: "not json")
    with pytest.raises(LaneError):
        text_llm.extract(str(corpus / "pdfs" / "cert_en_clean.pdf"), backend)


def test_vision_lane_sends_a_200_dpi_png(corpus):
    seen = []

    def handler(prompt, images):
        seen.append(images)
        return json.dumps({"rows": []})

    vision.extract(str(corpus / "pdfs" / "cert_en_wrapped.pdf"), FakeBackend(handler))
    assert len(seen) == 3
    assert all(img[0][:8] == b"\x89PNG\r\n\x1a\n" for img in seen)
    # A4 at 200 DPI is about 1654 x 2339 pixels (the example pages are 595 x 842 pt)
    assert int.from_bytes(seen[0][0][16:20], "big") == round(595 * 200 / 72)


def test_models_are_required_not_defaulted(monkeypatch, corpus):
    monkeypatch.delenv("TEXT_MODEL", raising=False)
    monkeypatch.delenv("VISION_MODEL", raising=False)
    monkeypatch.delenv("TEXT_BACKEND", raising=False)
    monkeypatch.delenv("VISION_BACKEND", raising=False)
    with pytest.raises(ConfigError):
        text_llm.extract(str(corpus / "pdfs" / "cert_en_clean.pdf"))
    with pytest.raises(ConfigError):
        vision.extract(str(corpus / "pdfs" / "cert_en_clean.pdf"))

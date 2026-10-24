import pymupdf

from bench.gate_demo import planted_missed
from corpus.pii_fixture import KEPT, PLANTED
from gate.detect import detect
from gate.gate import run_gate
from gate.verify import FakeVerifier, ResidueVerifier


def test_single_missed_identifier_fails_the_build(corpus, tmp_path):
    res = run_gate(corpus / "pdfs" / "pii_fixture.pdf", 1, tmp_path, FakeVerifier("PASS"))
    assert res.verdict == "PASS"
    assert planted_missed(res.redacted_text) == [], "an identifier survived redaction"
    # the redacted file really lost the text: it is not only painted over
    assert not any(p in res.redacted_text for p in PLANTED)


def test_the_planted_check_has_teeth(corpus, tmp_path):
    """A detector that misses the email must be caught by the planted-identifier check."""
    def blind(text):
        return [s for s in detect(text) if s.kind != "email" and "@" not in s.text]

    res = run_gate(corpus / "pdfs" / "pii_fixture.pdf", 1, tmp_path, FakeVerifier("PASS"), blind)
    assert planted_missed(res.redacted_text) == ["t.wren@example.org"]


def test_over_redaction_known_row_and_kept_fields_survive(corpus, tmp_path):
    res = run_gate(corpus / "pdfs" / "pii_fixture.pdf", 1, tmp_path, FakeVerifier("PASS"))
    assert "Pressure 50 % point reading" in res.redacted_text
    assert "5.01" in res.redacted_text and "4.98" in res.redacted_text
    assert all(k in res.redacted_text for k in KEPT)


def test_fail_closed_when_the_verifier_raises(corpus, tmp_path):
    res = run_gate(corpus / "pdfs" / "pii_fixture.pdf", 1, tmp_path,
                   FakeVerifier(RuntimeError("model down")))
    assert res.verdict == "BLOCK" and res.png_path is None
    assert list(tmp_path.glob("*.png")) == []


def test_fail_closed_on_refusal_or_unparseable_answer(corpus, tmp_path):
    for answer in ("FAIL", "I cannot help with that", "", None, "pass maybe"):
        res = run_gate(corpus / "pdfs" / "pii_fixture.pdf", 1, tmp_path, FakeVerifier(answer))
        assert res.verdict == "BLOCK", answer
        assert list(tmp_path.glob("*.png")) == []


def test_fail_closed_when_a_span_cannot_be_located(corpus, tmp_path):
    from gate.detect import Span

    res = run_gate(corpus / "pdfs" / "pii_fixture.pdf", 1, tmp_path, FakeVerifier("PASS"),
                   lambda text: [Span("not on this page at all", "label")])
    assert res.verdict == "BLOCK" and "locate" in res.reason
    assert list(tmp_path.glob("*.png")) == []


def test_png_exists_only_on_pass(corpus, tmp_path):
    res = run_gate(corpus / "pdfs" / "pii_fixture.pdf", 1, tmp_path, FakeVerifier("PASS"))
    assert res.png_path and res.png_path.exists()
    assert pymupdf.Pixmap(str(res.png_path)).width == round(595 * 200 / 72)


def test_residue_verifier_blocks_a_page_that_still_has_an_email():
    assert ResidueVerifier().verify(b"", "Email: someone@example.org") == "FAIL"
    assert ResidueVerifier().verify(b"", "Pressure reading 5.01 bar 4.98 5.02") == "PASS"

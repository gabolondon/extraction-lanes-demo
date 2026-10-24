"""Gate demo: the PII fixture and one certificate page. ``python -m bench.gate_demo``."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from corpus.pii_fixture import KEPT, PLANTED
from gate.gate import run_gate
from gate.verify import OllamaVerifier, ResidueVerifier
from score.scorer import norm_name

ROOT = Path(__file__).resolve().parent.parent


def planted_missed(text: str) -> list[str]:
    """Planted identifiers still present in the redacted page text."""
    flat = norm_name(text)
    return [p for p in PLANTED if norm_name(p) in flat]


def main() -> int:
    out = ROOT / "results" / "gate"
    verifier = OllamaVerifier() if os.environ.get("VERIFY_MODEL") else ResidueVerifier()
    print(f"verifier: {verifier.name}")
    failed = False
    for pdf, page, label in [
        (ROOT / "corpus/pdfs/pii_fixture.pdf", 1, "PII fixture"),
        (ROOT / "corpus/pdfs/cert_en_clean.pdf", 1, "certificate page"),
    ]:
        res = run_gate(pdf, page, out, verifier)
        print(f"\n[{label}] {pdf.name} page {page}: {res.verdict} ({res.reason})")
        print(f"  spans redacted: {len(res.spans)}  " + ", ".join(s.kind for s in res.spans))
        if label == "PII fixture":
            missed = planted_missed(res.redacted_text)
            print(f"  planted identifiers: {len(PLANTED) - len(missed)}/{len(PLANTED)} removed"
                  + (f"  MISSED: {missed}" if missed else ""))
            failed |= bool(missed)
            kept = [k for k in KEPT if k in res.redacted_text]
            print(f"  kept fields intact: {len(kept)}/{len(KEPT)};"
                  f" measurement row kept: {'Pressure 50 %' in res.redacted_text}")
        print(f"  png: {'written' if res.png_path else 'none (blocked or removed)'}")
        failed |= res.verdict != "PASS"
    print("\nGATE DEMO:", "FAIL" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

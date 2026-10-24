"""Verifiers: independent of the detector. Anything other than an explicit PASS blocks."""

from __future__ import annotations

import json
import os
import re

from lanes.backends import require_env

PROMPT = "Is any personal data still visible on this page? Answer PASS or FAIL."
SCHEMA = {
    "type": "object",
    "properties": {"verdict": {"type": "string", "enum": ["PASS", "FAIL"]}},
    "required": ["verdict"],
}


class OllamaVerifier:
    """A local vision model looks at the rendered PNG. Model is required via VERIFY_MODEL."""

    name = "ollama"
    fake = False

    def __init__(self, model: str | None = None):
        import ollama

        self.model = model or require_env("VERIFY_MODEL")
        self._client = ollama.Client(host=os.environ.get("OLLAMA_HOST"))

    def verify(self, png: bytes, text: str) -> str:
        r = self._client.generate(model=self.model, prompt=PROMPT, images=[png], format=SCHEMA,
                                  options={"temperature": 0})
        return json.loads(r.response)["verdict"]


class FakeVerifier:
    """Tests only. ``answer`` is returned, or raised if it is an exception."""

    name = "fake"
    fake = True

    def __init__(self, answer: str | Exception = "PASS"):
        self.answer = answer

    def verify(self, png: bytes, text: str) -> str:
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


_RESIDUE = [re.compile(p) for p in (r"@", r"\+\d", r":\s*\S*[A-Z][\wáéíóúñ]+ [A-Z][\wáéíóúñ]+")]


class ResidueVerifier:
    """Offline heuristic for the demo: scans the text that is left in the redacted page.

    Written separately from the detector (it knows no labels). It is a coarse smoke check, not a
    replacement for a vision model.
    """

    name = "residue-heuristic"
    fake = False

    def verify(self, png: bytes, text: str) -> str:
        for ln in text.splitlines():
            if re.search(r"\d+\.\d+", ln):  # measurement rows are expected to remain
                continue
            if any(p.search(ln) for p in _RESIDUE):
                return "FAIL"
        return "PASS"

"""Judge backends: ``fake`` (tests), ``ollama`` (local, option-letter log-probabilities), ``http``."""

from __future__ import annotations

import math
import os
import re

import httpx
from rapidfuzz import fuzz

from judge.core import LETTERS, Decision, Request, decision_from_logprobs, render_item

INSTRUCTION = (
    "You are a careful judge. For each item choose exactly one option. Reply with one line per "
    "item in the form `<item number>=<option letter>` and nothing else.\n\n"
)
FLOOR_LOGPROB = -20.0


class FakeBackend:
    """Offline stand-in. ``scorer(request) -> {choice: score}``; softmax of the scores."""

    name = "fake"
    leaves_machine = False
    fake = True

    def __init__(self, scorer=None, temperature: float = 8.0):
        self.scorer, self.temperature = scorer or default_scorer, temperature

    def decide_many(self, reqs: list[Request]) -> list[Decision]:
        return [
            decision_from_logprobs({c: s / self.temperature for c, s in self.scorer(r).items()})
            for r in reqs
        ]


def default_scorer(req: Request) -> dict[str, float]:
    """Deterministic heuristic used only to exercise the pipeline offline."""
    if "page text" in req.facts:  # line_attribution: the candidate closest above the value wins
        lines = req.facts["page text"].splitlines()
        value = re.search(r"value ([-\d.]+)", req.question)
        vidx = next((i for i, ln in enumerate(lines) if value and ln.strip() == value.group(1)),
                    len(lines))
        out = {}
        for c in req.choices:
            pos = [i for i, ln in enumerate(lines) if ln.strip() == c.strip()]
            out[c] = 100 - 12 * min((vidx - p for p in pos if p < vidx), default=9)
        return out
    name = str(req.facts["printed name"])
    out = {}
    for c in req.choices:
        if c == "none_of_these":
            out[c] = 55.0
            continue
        aliases = req.describe.get(c, c).split(" / ")
        out[c] = max(fuzz.partial_ratio(name.casefold(), a.casefold()) for a in aliases)
    return out


# ---- ollama ---------------------------------------------------------------------------------
def parse_batch_logprobs(entries: list, n_items: int, n_choices: list[int]) -> list[Decision]:
    """Find each ``k=<letter>`` answer in the generated tokens and read the option-letter
    log-probabilities at the letter position. ``entries`` are token log-prob records."""
    found: dict[int, dict[str, float]] = {}
    acc = ""
    for e in entries:
        m = re.search(r"(\d+)=\s*$", acc)
        if m and int(m.group(1)) not in found:
            k = int(m.group(1))
            if 1 <= k <= n_items:
                letters = LETTERS[: n_choices[k - 1]]
                lp = {letter: FLOOR_LOGPROB for letter in letters}
                for t in (e.top_logprobs or [e]):
                    tok = t.token.strip().upper()
                    if tok in lp:
                        lp[tok] = max(lp[tok], t.logprob)
                found[k] = lp
        acc += e.token
    if len(found) != n_items:
        raise ValueError(f"expected {n_items} answers in the output, found {len(found)}")
    return [decision_from_logprobs(found[k]) for k in range(1, n_items + 1)]


class OllamaBackend:
    name = "ollama"
    leaves_machine = False
    fake = False

    def __init__(self, model: str | None = None):
        import ollama

        self.model = model or os.environ.get("JUDGE_MODEL", "").strip()
        if not self.model:
            raise RuntimeError("JUDGE_MODEL is required: name a model you have pulled in Ollama.")
        self._client = ollama.Client(host=os.environ.get("OLLAMA_HOST"))

    def decide_many(self, reqs: list[Request]) -> list[Decision]:
        prompt = INSTRUCTION + "\n\n".join(render_item(r, i) for i, r in enumerate(reqs, 1))
        resp = self._client.generate(
            model=self.model, prompt=prompt, logprobs=True, top_logprobs=20,
            options={"temperature": 0, "num_predict": 8 * len(reqs) + 16},
        )
        picks = parse_batch_logprobs(resp.logprobs or [], len(reqs), [len(r.choices) for r in reqs])
        return [
            Decision(r.choices[LETTERS.index(max(d.probabilities, key=d.probabilities.get))],
                     {r.choices[LETTERS.index(k)]: v for k, v in d.probabilities.items()}, d.margin)
            for r, d in zip(reqs, picks, strict=True)
        ]


# ---- http -----------------------------------------------------------------------------------
class HttpBackend:
    """Generic endpoint. POST {"items": [{facts, question, choices}]} with a bearer key; expects
    {"decisions": [{"probabilities": {choice: p}}]}. Never called by the tests."""

    name = "http"
    leaves_machine = True
    fake = False

    def __init__(self, url: str | None = None, key: str | None = None):
        self.url = url or os.environ.get("JUDGE_URL", "")
        self.key = key or os.environ.get("JUDGE_KEY", "")

    def decide_many(self, reqs: list[Request]) -> list[Decision]:
        if not (self.url and self.key):
            raise RuntimeError("JUDGE_URL and JUDGE_KEY are required for the http backend")
        body = {"items": [{"facts": r.facts, "question": r.question, "choices": r.choices}
                          for r in reqs]}
        r = httpx.post(self.url, json=body, headers={"Authorization": f"Bearer {self.key}"},
                       timeout=60)
        r.raise_for_status()
        out = []
        for dec in r.json()["decisions"]:
            lp = {c: math.log(max(p, 1e-9)) for c, p in dec["probabilities"].items()}
            out.append(decision_from_logprobs(lp))
        return out


def make_backend(kind: str):
    return {"fake": FakeBackend, "ollama": OllamaBackend, "http": HttpBackend}[kind]()

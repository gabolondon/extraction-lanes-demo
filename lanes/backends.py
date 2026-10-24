"""Model backends for the text and vision lanes: ``ollama`` (local) or ``fake`` (tests only)."""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass

from lanes.base import LaneError


@dataclass
class Completion:
    text: str
    truncated: bool = False  # the model stopped on the length limit


class ConfigError(LaneError):
    pass


def require_env(var: str) -> str:
    val = os.environ.get(var, "").strip()
    if not val:
        raise ConfigError(f"{var} is required: name a model you have pulled in Ollama.")
    return val


class OllamaBackend:
    name = "ollama"
    fake = False

    def __init__(self, model: str, host: str | None = None, num_predict: int = 4096):
        import ollama

        self.model, self.num_predict = model, num_predict
        self._client = ollama.Client(host=host or os.environ.get("OLLAMA_HOST"))

    def complete(self, prompt: str, schema: dict, images: list[bytes] | None = None) -> Completion:
        resp = self._client.generate(
            model=self.model,
            prompt=prompt,
            images=images,
            format=schema,
            options={"temperature": 0, "num_predict": self.num_predict},
        )
        return Completion(resp.response, truncated=(resp.done_reason == "length"))


class FakeBackend:
    """Offline stand-in. ``handler(prompt, images) -> str | Completion``."""

    name = "fake"
    fake = True

    def __init__(self, handler: Callable[[str, list[bytes] | None], str | Completion]):
        self.handler = handler

    def complete(self, prompt: str, schema: dict, images: list[bytes] | None = None) -> Completion:
        out = self.handler(prompt, images)
        return out if isinstance(out, Completion) else Completion(out)


_NUM = re.compile(r"^-?\d+\.\d+$")


def line_parser_handler(prompt: str, images: list[bytes] | None) -> str:
    """A tiny 'model' for demos: reads name/value/unit/min/max five-line groups out of the prompt
    text. It sees no images and fails on any other layout."""
    import json

    lines = [ln.strip() for ln in prompt.split("PAGE TEXT:\n", 1)[-1].splitlines() if ln.strip()]
    rows = []
    for i in range(len(lines) - 4):
        n, v, u, lo, hi = lines[i:i + 5]
        if _NUM.match(v) and _NUM.match(lo) and _NUM.match(hi) and not _NUM.match(u):
            rows.append(dict(printed_label=n, value=v, unit=u, min=lo, max=hi, verbatim=" ".join(lines[i:i + 5])))
    return json.dumps({"rows": rows})


def make_backend(kind: str, model_var: str):
    if kind == "fake":
        return FakeBackend(line_parser_handler)
    if kind == "ollama":
        return OllamaBackend(require_env(model_var))
    raise ConfigError(f"unknown backend {kind!r}: use ollama or fake")

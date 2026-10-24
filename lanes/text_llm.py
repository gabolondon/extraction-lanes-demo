"""Text lane: page text in, schema-constrained JSON rows out."""

from __future__ import annotations

import os

import pymupdf

from lanes.backends import make_backend
from lanes.base import Row
from lanes.llm_common import INSTRUCTIONS, ROW_SCHEMA, parse_rows


def extract(doc_path: str, backend=None) -> list[Row]:
    backend = backend or make_backend(os.environ.get("TEXT_BACKEND", "ollama"), "TEXT_MODEL")
    rows: list[Row] = []
    with pymupdf.open(doc_path) as doc:
        for page in doc:
            prompt = f"{INSTRUCTIONS}\n\nPAGE TEXT:\n{page.get_text()}"
            rows += parse_rows(page.number + 1, backend.complete(prompt, ROW_SCHEMA))
    return rows

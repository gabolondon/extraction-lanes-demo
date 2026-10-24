"""Vision lane: 200-DPI page image in, schema-constrained JSON rows out."""

from __future__ import annotations

import os

import pymupdf

from lanes.backends import make_backend
from lanes.base import Row
from lanes.llm_common import INSTRUCTIONS, ROW_SCHEMA, parse_rows

DPI = 200


def render_png(page: pymupdf.Page) -> bytes:
    return page.get_pixmap(dpi=DPI).tobytes("png")


def extract(doc_path: str, backend=None) -> list[Row]:
    backend = backend or make_backend(os.environ.get("VISION_BACKEND", "ollama"), "VISION_MODEL")
    rows: list[Row] = []
    with pymupdf.open(doc_path) as doc:
        for page in doc:
            comp = backend.complete(INSTRUCTIONS, ROW_SCHEMA, images=[render_png(page)])
            rows += parse_rows(page.number + 1, comp)
    return rows

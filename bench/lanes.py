"""Lane bench: one table, lane x document. ``python -m bench.lanes --lanes layout``."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path

import pymupdf

from lanes.backends import ConfigError
from lanes.base import LaneError
from lanes.text_layer import check_pdf
from score import load_gold, score

ROOT = Path(__file__).resolve().parent.parent
DOCS = ["cert_en_clean", "cert_es_stacked", "cert_en_wrapped"]
LANES = {"layout": "lanes.layout", "text_llm": "lanes.text_llm", "vision": "lanes.vision"}
ENV = {"text_llm": "TEXT_BACKEND", "vision": "VISION_BACKEND"}


def _is_fake(lane: str) -> bool:
    import os

    return lane in ENV and os.environ.get(ENV[lane]) == "fake"


def run(lanes: list[str], corpus: Path, out: Path) -> list[dict]:
    results = []
    for doc in DOCS:
        pdf = corpus / "pdfs" / f"{doc}.pdf"
        gold = load_gold(corpus / "gold" / f"{doc}.csv")
        broken = sum(r.broken for r in check_pdf(str(pdf)))
        with pymupdf.open(pdf) as d:
            n_pages = len(d)
        for lane in lanes:
            mod = importlib.import_module(LANES[lane])
            t0 = time.perf_counter()
            try:
                rows = mod.extract(str(pdf))
            except (LaneError, ConfigError) as exc:
                results.append(dict(lane=lane, doc=doc, error=str(exc), broken_pages=broken))
                continue
            sc = score(rows, gold, n_pages, time.perf_counter() - t0)
            results.append(dict(lane=lane, doc=doc, broken_pages=broken, fake=_is_fake(lane),
                                **sc.__dict__))
    out.mkdir(parents=True, exist_ok=True)
    (out / "lanes.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out / "lanes.md").write_text(table(results) + "\n", encoding="utf-8")
    return results


def table(results: list[dict]) -> str:
    head = ("| lane | document | strict % | precision | recall | phantom | zero-row pages "
            "| s/page | text layer |\n|---|---|---|---|---|---|---|---|---|")
    lines = [head]
    for r in results:
        layer = f"broken ({r['broken_pages']} pages)" if r["broken_pages"] else "ok"
        tag = " (fake backend)" if r.get("fake") else ""
        if "error" in r:
            lines.append(f"| {r['lane']}{tag} | {r['doc']} | ERROR: {r['error']} | | | | | | "
                         f"{layer} |")
            continue
        lines.append(
            f"| {r['lane']}{tag} | {r['doc']} | {100 * r['strict']:.0f} "
            f"| {r['precision']:.2f} | {r['recall']:.2f} | {r['phantom']} "
            f"| {r['zero_row_pages']} | {r['seconds_per_page']:.2f} | {layer} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lanes", default="layout", help="comma list: layout,text_llm,vision")
    ap.add_argument("--corpus", default=str(ROOT / "corpus"))
    ap.add_argument("--out", default=str(ROOT / "results"))
    a = ap.parse_args(argv)
    lanes = [x.strip() for x in a.lanes.split(",") if x.strip()]
    unknown = [x for x in lanes if x not in LANES]
    if unknown:
        print(f"unknown lane(s): {unknown}", file=sys.stderr)
        return 2
    res = run(lanes, Path(a.corpus), Path(a.out))
    print(table(res))
    if any(r.get("fake") for r in res):
        print("\n(fake backend) rows come from an offline stand-in, not from a model: not a result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

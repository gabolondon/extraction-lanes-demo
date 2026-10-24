"""``python -m judge.cli bench`` and ``python -m judge.cli policy-demo``."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from judge.backends import HttpBackend, make_backend
from judge.core import EgressRefused, Policy, run_task, summarize
from judge.tasks import TASKS, attribution_cases, field_mapping_cases

ROOT = Path(__file__).resolve().parent.parent
THRESHOLD = 0.5


def bench(kind: str, batch: int, concurrency: int, corpus: Path, out: Path,
          threshold: float = THRESHOLD) -> int:
    backend = make_backend(kind)
    cases = {"field_mapping": field_mapping_cases(corpus),
             "line_attribution": attribution_cases(corpus)}
    rows, refused = [], []
    for name, task in TASKS.items():
        t0 = time.perf_counter()
        try:
            outcomes = run_task(task, cases[name], backend, Policy(), batch, concurrency)
        except EgressRefused as exc:
            refused.append(str(exc))
            continue
        secs = time.perf_counter() - t0
        s = summarize(task, outcomes, threshold)
        rows.append(dict(task=name, backend=backend.name, fake=backend.fake, batch=batch,
                         concurrency=concurrency, seconds=round(secs, 2), **s.__dict__))
    tag = " (fake backend)" if backend.fake else ""
    lines = ["| task | n | accuracy | confident errors | auto-accepted | accuracy on auto | seconds |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['task']}{tag} | {r['n']} | {r['accuracy']:.2f} | "
                     f"{r['confident_errors']} | {100 * r['share_auto']:.0f}% | "
                     f"{r['accuracy_auto']:.2f} | {r['seconds']} |")
    table = "\n".join(lines)
    print(f"backend={backend.name} batch={batch} concurrency={concurrency} "
          f"threshold={threshold}{tag}\n{table}")
    for msg in refused:
        print("REFUSED:", msg)
    if backend.fake:
        print("(fake backend) offline stand-in: not a result.")
    out.mkdir(parents=True, exist_ok=True)
    (out / "judge.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out / "judge.md").write_text(table + "\n", encoding="utf-8")
    return 0


def policy_demo() -> int:
    backend = HttpBackend(url=os.environ.get("JUDGE_URL") or "https://judge.invalid/decide",
                          key=os.environ.get("JUDGE_KEY") or "unset")
    print(f"backend: {backend.name} (leaves_machine={backend.leaves_machine})")
    for task in TASKS.values():
        try:
            Policy().check(task, backend)
            print(f"  {task.name:<17} data_class={task.data_class:<8} -> allowed "
                  "(this demo makes no call)")
        except EgressRefused as exc:
            print(f"  {task.name:<17} data_class={task.data_class:<8} -> REFUSED: {exc}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bench")
    b.add_argument("--judge", default=os.environ.get("JUDGE", "fake"),
                   choices=["fake", "ollama", "http"])
    b.add_argument("--batch", type=int, default=int(os.environ.get("BATCH", 1)))
    b.add_argument("--concurrency", type=int, default=int(os.environ.get("CONCURRENCY", 1)))
    b.add_argument("--corpus", default=str(ROOT / "corpus"))
    b.add_argument("--out", default=str(ROOT / "results"))
    sub.add_parser("policy-demo")
    a = ap.parse_args(argv)
    if a.cmd == "policy-demo":
        return policy_demo()
    return bench(a.judge, a.batch, a.concurrency, Path(a.corpus), Path(a.out))


if __name__ == "__main__":
    sys.exit(main())

"""Matcher bench: naive vs fixed on the field-mapping task. ``python -m bench.matcher``."""

from __future__ import annotations

import json
from pathlib import Path

from catalog.data import CATALOG, NONE_OF_THESE
from catalog.matcher import FixedMatcher, NaiveMatcher, derive_filler
from judge.tasks import field_mapping_cases

ROOT = Path(__file__).resolve().parent.parent
CONFIDENT_MARGIN = 0.10


def evaluate(matcher, cases: list[dict]) -> dict:
    correct = conf_err = 0
    collapsed: dict[str, set[str]] = {}
    for c in cases:
        m = matcher.match(c["printed_label"])
        correct += m.code == c["code"]
        if m.code != NONE_OF_THESE and m.code != c["code"]:
            collapsed.setdefault(m.code, set()).add(c["code"])
            conf_err += m.margin >= CONFIDENT_MARGIN
    worst = max(collapsed.items(), key=lambda kv: len(kv[1]), default=("-", set()))
    return dict(matcher=matcher.name, n=len(cases), correct=correct,
                accuracy=correct / len(cases), confident_errors=conf_err,
                codes_absorbing_others=len([k for k, v in collapsed.items() if len(v) > 1]),
                most_absorbed=(worst[0], len(worst[1])))


def main() -> int:
    cases = field_mapping_cases(ROOT / "corpus")
    filler = sorted(derive_filler(CATALOG))
    print(f"{len(cases)} printed names from the example corpus; {len(CATALOG)} catalog codes")
    print(f"filler words derived from the catalog (in > 1/3 of aliases): {', '.join(filler)}")
    results = [evaluate(m, cases) for m in (NaiveMatcher(), FixedMatcher())]
    head = ("| matcher | correct | accuracy | confident errors (margin >= "
            f"{CONFIDENT_MARGIN}) | codes absorbing several others |\n|---|---|---|---|---|")
    body = [f"| {r['matcher']} | {r['correct']}/{r['n']} | {r['accuracy']:.2f} | "
            f"{r['confident_errors']} | {r['codes_absorbing_others']} |" for r in results]
    table = "\n".join([head, *body])
    print(table)
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "matcher.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out / "matcher.md").write_text(table + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

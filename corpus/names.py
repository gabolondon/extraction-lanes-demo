"""Printed-name variants: how the example labs write the same parameter in different ways."""

from __future__ import annotations

import random
from dataclasses import dataclass

from catalog.data import CATALOG, OFF_CATALOG, POINTS, QUANTITIES, Entry

_POINT_PARTS = {}
for _q in QUANTITIES:
    for _pt in POINTS:
        _POINT_PARTS[f"{_q[:4].upper()}_{_pt.split()[0].upper().replace('%', 'PCT')}"
                     + ("_FS" if _pt == "full scale" else "")] = (_q, _pt)

# Suffixes that make a printed name longer than the catalog alias.
EN_TAILS = ["ascending", "descending", "run 2", "after conditioning", "bench A"]
ES_TAILS = ["ascendente", "descendente", "ciclo 2", "tras acondicionamiento", "banco A"]


@dataclass(frozen=True)
class RowSpec:
    name: str
    code: str  # catalog code or "none_of_these"
    unit: str
    lo: float
    hi: float


def printed_name(rng: random.Random, entry: Entry, lang: str) -> str:
    """One of several printings of the entry's name. Variant 0 is the catalog alias."""
    v = rng.choice([0, 0, 1, 2])
    parts = _POINT_PARTS.get(entry.code)
    tails = EN_TAILS if lang == "en" else ES_TAILS
    if parts:
        q, pt = parts
        q_es, pt_es = QUANTITIES[q][0], POINTS[pt][0]
        if lang == "en":
            base = [entry.en[0], f"Reading point {pt}: {q}", f"{q.capitalize()} at {pt} point"][v]
        else:
            base = [
                entry.es[0],
                f"Punto {pt_es} - lectura de {q_es}",
                f"{q_es.capitalize()} en punto {pt_es}",
            ][v]
    else:
        alias = entry.en[0] if lang == "en" else entry.es[0]
        words = alias
        if lang == "en":
            base = [alias, f"Reading point 3: {words}", f"{words.capitalize()}, bench check"][v]
        else:
            base = [alias, f"Punto 3 - {words}", f"{words.capitalize()}, control de banco"][v]
    if v == 2 and rng.random() < 0.5:
        base += ", " + rng.choice(tails)
    return base[0].upper() + base[1:]


def build_rows(rng: random.Random, lang: str, n: int, extra_tail: bool = False) -> list[RowSpec]:
    """n rows with unique printed names; ~1 in 9 are names that are not in the catalog."""
    rows: list[RowSpec] = []
    seen: set[str] = set()
    pool = list(CATALOG)
    rng.shuffle(pool)
    i = 0
    while len(rows) < n:
        if rng.random() < 0.11:
            en, es, unit, lo, hi = rng.choice(OFF_CATALOG)
            name = (en if lang == "en" else es).capitalize()
            code = "none_of_these"
        else:
            e = pool[i % len(pool)]
            i += 1
            name = printed_name(rng, e, lang)
            code, unit, lo, hi = e.code, e.unit, e.lo, e.hi
        if extra_tail:
            name += (
                ", ascending run 2 (after thermal conditioning)"
                if lang == "en"
                else ", ciclo ascendente 2 (tras acondicionamiento térmico)"
            )
        base, k = name, 2
        while name in seen:
            name = f"{base}, {'run' if lang == 'en' else 'ciclo'} {k}"
            k += 1
        seen.add(name)
        rows.append(RowSpec(name, code, unit, lo, hi))
    return rows

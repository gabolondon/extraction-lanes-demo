"""Two matchers kept side by side so the bench can show the difference.

``naive``  : partial_ratio on the printed name as it appears.
``fixed``  : drop filler words derived from the catalog itself, then token_set_ratio with a floor.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from rapidfuzz import fuzz

from catalog.data import CATALOG, NONE_OF_THESE, Entry

FLOOR = 0.80
FILLER_SHARE = 1 / 3
INVISIBLE = dict.fromkeys(map(ord, "­​‌‍⁠﻿"), None)
_TOKEN = re.compile(r"[\w%°]+", re.UNICODE)


def normalize(text: str) -> str:
    return " ".join(_TOKEN.findall(text.translate(INVISIBLE).casefold()))


def derive_filler(catalog: list[Entry] = CATALOG, share: float = FILLER_SHARE) -> frozenset[str]:
    """Words present in more than ``share`` of all aliases (document frequency)."""
    aliases = [a for e in catalog for a in e.aliases]
    df = Counter(w for a in aliases for w in set(normalize(a).split()))
    return frozenset(w for w, n in df.items() if n / len(aliases) > share)


@dataclass(frozen=True)
class Match:
    code: str  # a catalog code or NONE_OF_THESE
    score: float  # 0..1 of the best code
    margin: float  # best minus second best code, 0..1
    ranked: tuple[tuple[str, float], ...]  # (code, score), best first


def _decide(scores: dict[str, float], floor: float) -> Match:
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    best_code, best = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    code = best_code if best >= floor else NONE_OF_THESE
    return Match(code, best, best - second, tuple(ranked))


class NaiveMatcher:
    name = "naive"

    def __init__(self, catalog: list[Entry] = CATALOG, floor: float = 0.0):
        # no floor: the naive matcher always names a code, even for a name that is in none of them
        self.catalog, self.floor = catalog, floor

    def match(self, printed: str) -> Match:
        p = printed.casefold()
        scores = {
            e.code: max(fuzz.partial_ratio(p, a.casefold()) for a in e.aliases) / 100
            for e in self.catalog
        }
        return _decide(scores, self.floor)


class FixedMatcher:
    name = "fixed"

    def __init__(self, catalog: list[Entry] = CATALOG, floor: float = FLOOR):
        self.catalog, self.floor = catalog, floor
        self.filler = derive_filler(catalog)
        self._aliases = {e.code: [self._strip(a) for a in e.aliases] for e in catalog}

    def _strip(self, text: str) -> str:
        return " ".join(w for w in normalize(text).split() if w not in self.filler)

    def match(self, printed: str) -> Match:
        p = self._strip(printed)
        scores = {
            code: max(fuzz.token_set_ratio(p, a) for a in aliases) / 100
            for code, aliases in self._aliases.items()
        }
        return _decide(scores, self.floor)

    def shortlist(self, printed: str, k: int = 5) -> list[str]:
        return [c for c, _ in self.match(printed).ranked[:k]]

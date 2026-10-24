from catalog.data import CATALOG, Entry
from catalog.matcher import FixedMatcher, NaiveMatcher, derive_filler
from judge.tasks import field_mapping_cases


def test_filler_is_derived_from_the_catalog():
    assert {"reading", "point", "lectura", "punto"} <= derive_filler(CATALOG)
    tiny = [Entry("A", ("alpha widget",), (), "x", 0, 1), Entry("B", ("beta widget",), (), "x", 0, 1),
            Entry("C", ("gamma gizmo",), (), "x", 0, 1)]
    assert derive_filler(tiny) == frozenset({"widget"})  # 2 of 3 aliases, > 1/3


def test_fixed_beats_naive_on_the_example_corpus(corpus):
    cases = field_mapping_cases(corpus)
    naive, fixed = NaiveMatcher(), FixedMatcher()
    n_ok = sum(naive.match(c["printed_label"]).code == c["code"] for c in cases)
    f_ok = sum(fixed.match(c["printed_label"]).code == c["code"] for c in cases)
    assert f_ok > n_ok and f_ok / len(cases) > 0.95


def test_fixed_floor_returns_none_of_these_for_unknown_names():
    assert FixedMatcher().match("Warm-up time").code == "none_of_these"


def test_naive_always_names_a_code():
    assert NaiveMatcher().match("Warm-up time").code != "none_of_these"

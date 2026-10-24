from lanes.base import Row
from score import score


def row(page, name, v="1.00", u="bar", lo="0.00", hi="2.00"):
    return Row(page, name, v, u, lo, hi)


def test_name_match_ignores_spaces_case_and_invisible_characters():
    gold = [row(1, "Presión cero")]
    pred = [row(1, "pre​sión  c­ero")]
    s = score(pred, gold, 1, 1.0)
    assert s.strict == 1.0 and s.precision == 1.0 and s.phantom == 0


def test_strict_needs_unit_and_both_bounds():
    gold = [row(1, "a")]
    assert score([row(1, "a", u="mbar")], gold, 1, 1).strict == 0.0
    assert score([row(1, "a", hi="9.00")], gold, 1, 1).strict == 0.0
    s = score([row(1, "a", u="mbar")], gold, 1, 1)
    assert s.recall == 1.0  # name + value still match


def test_phantom_and_zero_row_pages_and_seconds():
    gold = [row(1, "a"), row(2, "b")]
    s = score([row(1, "a"), row(1, "ghost")], gold, 2, 4.0)
    assert s.phantom == 1 and s.zero_row_pages == 1
    assert s.precision == 0.5 and s.recall == 0.5 and s.seconds_per_page == 2.0


def test_numbers_compare_as_numbers():
    assert score([row(1, "a", v="1.0")], [row(1, "a", v="1.00")], 1, 1).strict == 1.0

import types

import httpx
import pytest

from judge.backends import FakeBackend, HttpBackend, parse_batch_logprobs
from judge.core import EgressRefused, Policy, Request, decision_from_logprobs, run_task, summarize
from judge.tasks import FIELD_MAPPING, LINE_ATTRIBUTION, attribution_cases, field_mapping_cases


def test_margin_is_top_minus_second():
    d = decision_from_logprobs({"A": 0.0, "B": -1.0, "C": -5.0})
    assert d.pick == "A"
    ps = sorted(d.probabilities.values(), reverse=True)
    assert d.margin == pytest.approx(ps[0] - ps[1])
    assert sum(d.probabilities.values()) == pytest.approx(1.0)


def test_policy_refuses_personal_on_a_remote_backend_before_any_network_call(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network was called")

    monkeypatch.setattr(httpx, "post", boom)
    backend = HttpBackend(url="https://judge.invalid/decide", key="k")
    with pytest.raises(EgressRefused):
        run_task(LINE_ATTRIBUTION, [{"lines": ["x"], "value": "1", "unit": "", "candidates": [],
                                     "truth": "skip"}], backend)


def test_policy_allows_personal_on_a_local_backend_and_public_on_a_remote_one():
    p = Policy()
    p.check(LINE_ATTRIBUTION, FakeBackend())
    p.check(FIELD_MAPPING, types.SimpleNamespace(name="remote", leaves_machine=True))
    with pytest.raises(EgressRefused):
        p.check(LINE_ATTRIBUTION, types.SimpleNamespace(name="remote", leaves_machine=True))


class Counting(FakeBackend):
    def __init__(self):
        super().__init__()
        self.sizes = []

    def decide_many(self, reqs):
        self.sizes.append(len(reqs))
        return super().decide_many(reqs)


def test_batching_groups_items_and_keeps_order(corpus):
    cases = field_mapping_cases(corpus)[:23]
    b = Counting()
    out = run_task(FIELD_MAPPING, cases, b, batch=5, concurrency=3)
    assert sorted(b.sizes) == [3, 5, 5, 5, 5]
    assert [o.item["printed_label"] for o in out] == [c["printed_label"] for c in cases]
    serial = run_task(FIELD_MAPPING, cases, FakeBackend(), batch=1)
    assert [o.decision.pick for o in out] == [o.decision.pick for o in serial]


def test_confident_error_excludes_abstentions(corpus):
    cases = field_mapping_cases(corpus)[:40]

    def always_none(req):
        return {c: (100.0 if c == "none_of_these" else 0.0) for c in req.choices}

    out = run_task(FIELD_MAPPING, cases, FakeBackend(always_none))
    s = summarize(FIELD_MAPPING, out, threshold=0.5)
    assert s.share_auto == 1.0 and s.confident_errors == 0 and s.accuracy < 1.0


def test_confident_error_counts_wrong_auto_accepted_picks(corpus):
    cases = field_mapping_cases(corpus)[:30]

    def always_first(req):
        return {c: (100.0 if c == req.choices[0] else 0.0) for c in req.choices}

    out = run_task(FIELD_MAPPING, cases, FakeBackend(always_first))
    s = summarize(FIELD_MAPPING, out, 0.5)
    expected = sum(o.decision.pick != o.truth for o in out)
    assert s.share_auto == 1.0 and s.confident_errors == expected > 0


def test_attribution_cases_are_built_from_the_corpus(corpus):
    cases = attribution_cases(corpus)
    assert any(c["truth"] == "skip" for c in cases)
    assert all(c["truth"] in c["candidates"] or c["truth"] == "skip" for c in cases)
    out = run_task(LINE_ATTRIBUTION, cases, FakeBackend())
    assert len(out) == len(cases)


def _tok(token, top=None):
    return types.SimpleNamespace(token=token, logprob=0.0,
                                 top_logprobs=[types.SimpleNamespace(token=t, logprob=lp)
                                               for t, lp in (top or [])])


def test_batch_logprob_parser_reads_the_letter_positions():
    entries = [_tok("1"), _tok("="), _tok("B", [("B", -0.1), (" A", -2.5), ("C", -9.0)]),
               _tok("\n"), _tok("2"), _tok("="), _tok("A", [("A", -0.3), ("B", -1.4)])]
    d = parse_batch_logprobs(entries, 2, [3, 2])
    assert d[0].pick == "B" and d[1].pick == "A"
    assert d[0].probabilities["A"] > d[0].probabilities["C"]


def test_batch_logprob_parser_rejects_missing_answers():
    with pytest.raises(ValueError):
        parse_batch_logprobs([_tok("1"), _tok("="), _tok("A", [("A", -0.1)])], 2, [2, 2])


def test_request_choices_round_trip():
    r = Request({"k": "v"}, "q?", ["x", "y"])
    assert r.choices == ["x", "y"]

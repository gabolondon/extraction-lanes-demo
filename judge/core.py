"""Typed judge: the wire format, the egress policy and the router.

``decide(facts, question, choices) -> Decision(pick, probabilities, margin)``; margin is the gap
between the two most probable choices. A pick is auto-accepted when margin >= threshold.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass(frozen=True)
class Decision:
    pick: str
    probabilities: dict[str, float]
    margin: float


@dataclass(frozen=True)
class Request:
    facts: dict
    question: str
    choices: list[str]
    describe: dict[str, str] = field(default_factory=dict)  # optional text shown next to a choice


def decision_from_logprobs(logprobs: dict[str, float]) -> Decision:
    """Softmax over the options (renormalised: probability mass outside them is ignored)."""
    m = max(logprobs.values())
    exp = {k: math.exp(v - m) for k, v in logprobs.items()}
    z = sum(exp.values())
    probs = {k: v / z for k, v in exp.items()}
    ranked = sorted(probs.values(), reverse=True)
    pick = max(probs, key=probs.__getitem__)
    return Decision(pick, probs, ranked[0] - (ranked[1] if len(ranked) > 1 else 0.0))


def render_item(req: Request, number: int | None = None) -> str:
    head = f"Item {number}\n" if number is not None else ""
    facts = "\n".join(f"{k}: {v}" for k, v in req.facts.items())
    opts = "\n".join(
        f"{LETTERS[i]}. {c}" + (f" ({req.describe[c]})" if c in req.describe else "")
        for i, c in enumerate(req.choices)
    )
    return f"{head}{facts}\nQuestion: {req.question}\n{opts}"


# ---- egress policy --------------------------------------------------------------------------
class EgressRefused(RuntimeError):
    pass


@dataclass(frozen=True)
class Task:
    name: str
    data_class: str  # "public" | "personal"
    build: Callable[[dict], Request]
    truth: Callable[[dict, Request], str]
    abstain: tuple[str, ...]  # picks that never count as a confident error


class Policy:
    """Refuses a personal-class task on a backend that leaves the machine, before any call."""

    def check(self, task: Task, backend) -> None:
        if task.data_class not in ("public", "personal"):
            raise EgressRefused(f"task {task.name!r}: unknown data_class {task.data_class!r}")
        if task.data_class == "personal" and backend.leaves_machine:
            raise EgressRefused(
                f"task {task.name!r} is class 'personal' and backend {backend.name!r} "
                "leaves the machine: refused before any network call"
            )


# ---- router ---------------------------------------------------------------------------------
@dataclass
class Outcome:
    item: dict
    request: Request
    decision: Decision
    truth: str


def run_task(task: Task, items: list[dict], backend, policy: Policy | None = None,
             batch: int = 1, concurrency: int = 1) -> list[Outcome]:
    (policy or Policy()).check(task, backend)  # first, before anything is sent
    reqs = [task.build(it) for it in items]
    chunks = [reqs[i:i + batch] for i in range(0, len(reqs), batch)]
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        decided = list(pool.map(backend.decide_many, chunks))
    decisions = [d for chunk in decided for d in chunk]
    if len(decisions) != len(items):
        raise RuntimeError("backend returned a different number of decisions than requests")
    return [Outcome(it, rq, d, task.truth(it, rq)) for it, rq, d in zip(items, reqs, decisions,
                                                                          strict=True)]


@dataclass
class Summary:
    n: int
    accuracy: float
    share_auto: float
    accuracy_auto: float
    confident_errors: int


def summarize(task: Task, outcomes: list[Outcome], threshold: float) -> Summary:
    auto = [o for o in outcomes if o.decision.margin >= threshold]
    right_auto = sum(o.decision.pick == o.truth for o in auto)
    conf_err = sum(o.decision.pick != o.truth and o.decision.pick not in task.abstain for o in auto)
    return Summary(
        n=len(outcomes),
        accuracy=sum(o.decision.pick == o.truth for o in outcomes) / len(outcomes),
        share_auto=len(auto) / len(outcomes),
        accuracy_auto=right_auto / len(auto) if auto else 0.0,
        confident_errors=conf_err,
    )

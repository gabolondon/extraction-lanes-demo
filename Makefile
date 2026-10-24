.PHONY: install corpus test lint bench-lanes gate-demo bench-matcher bench-judge policy-demo

LANES ?= layout
JUDGE ?= fake
BATCH ?= 1
CONCURRENCY ?= 1

install:
	uv sync

corpus:
	uv run python -m corpus.generate

test:
	uv run pytest -q
	uv run ruff check .

lint:
	uv run ruff check .

bench-lanes:
	uv run python -m bench.lanes --lanes $(LANES)

gate-demo:
	uv run python -m bench.gate_demo

bench-matcher:
	uv run python -m bench.matcher

# needs JUDGE=ollama JUDGE_MODEL=<a model you pulled>; JUDGE=fake only exercises the pipeline
bench-judge:
	uv run python -m judge.cli bench --judge $(JUDGE) --batch $(BATCH) --concurrency $(CONCURRENCY)

policy-demo:
	uv run python -m judge.cli policy-demo

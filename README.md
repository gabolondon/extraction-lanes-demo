# extraction-lanes-demo

This is example code: it shows the pattern I used, not the production implementation.

A small, runnable example of four ideas for pulling structured rows out of PDFs when some of the
pages carry personal data:

1. **Extraction lanes.** Three ways to read the same page behind one interface,
   `extract(doc_path) -> list[Row]`: a deterministic layout lane, a text-model lane and a vision
   lane. A scorer compares each lane with a gold answer, and a text-layer check says when the PDF's
   own text cannot be trusted, so the bench reports "broken text layer" instead of blaming a lane.
2. **A fail-closed redaction gate.** Detect, redact (the text is really removed), render a
   200-DPI PNG, then an independent check. Anything but an explicit pass blocks, and the PNG is
   deleted.
3. **A typed judge.** `decide(facts, question, choices) -> Decision(pick, probabilities, margin)`.
   A pick is auto-accepted when its margin clears a threshold. Each task declares a data class, each
   backend declares whether it leaves the machine, and a policy refuses a personal-class task on a
   backend that leaves the machine, before any network call.
4. **A catalog matcher, two versions side by side.** `naive` and `fixed`, so the bench can show what
   a small, data-derived change does to the same names.

## The example domain

Calibration certificates for industrial instruments (pressure gauges, thermometers, flow meters)
issued by two example labs, "Northwind Metrology" and "Laboratorio Andino de Calibración". Each
certificate has a header (technician, customer contact, phone, email, certificate number, site
address, calibration date, instrument model) followed by long tables of
`parameter | measured value | unit | tolerance min | tolerance max`. All names, companies and
numbers are examples.

`make corpus` writes, deterministically (fixed seed):

| file | what it exercises |
|---|---|
| `corpus/pdfs/cert_en_clean.pdf` | English, 4 pages, one line per row, clean text layer |
| `corpus/pdfs/cert_es_stacked.pdf` | Spanish, 4 pages, value / unit / tolerance stacked under the name; the text layer is broken but the page renders fine |
| `corpus/pdfs/cert_en_wrapped.pdf` | English, 3 pages, long names wrap, labels sit far from values, one page has no rows |
| `corpus/pdfs/pii_fixture.pdf` | one page with exactly 7 planted identifiers |
| `corpus/gold/*.csv` | `page, printed_label, value, unit, min, max` |

Gold is known by construction: the rows are generated first and drawn second.

## Run it

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```
make install        # uv sync
make corpus         # write the example PDFs and gold CSVs
make test           # offline; every model backend is replaced by a fake one
make bench-lanes    # layout lane only (no model needed); results/lanes.{json,md}
make gate-demo      # gate on the PII fixture and on one certificate page
make bench-matcher  # naive vs fixed matcher on the field-mapping task
make policy-demo    # the egress policy refusing a personal-class task on a remote backend
make bench-judge    # see below
```

### Model lanes (optional)

The model lanes need [Ollama](https://ollama.com) and a model of your choice. No model is
configured by default; the variables are required:

```
TEXT_MODEL=<your text model>   VISION_MODEL=<your vision model>   make bench-lanes LANES=layout,text_llm,vision
JUDGE=ollama JUDGE_MODEL=<your model> BATCH=8 CONCURRENCY=2 make bench-judge
VERIFY_MODEL=<your vision model> make gate-demo     # use a model as the gate's verifier
```

The judge's `ollama` backend reads token log-probabilities over the option letters, so it needs a
server and a model that return them. The `http` backend talks to a generic endpoint given by
`JUDGE_URL` and `JUDGE_KEY` (request and response shape are in `judge/backends.py`); the tests never
call it.

`fake` backends exist only so the tests run offline. Any bench line produced by one prints
"(fake backend)" and is not a result.

## Reading the numbers

The numbers here come from this example corpus, not from the work the blog post describes. The
layout lane is exact on the clean table and is expected to fail on the stacked one; that is the
assumption "one line is one row" showing its limit, and it is left unfixed on purpose.
Scores: *strict* needs name, value, unit and both bounds to match a gold row; precision and recall
use name and value, ignoring spaces and invisible characters; *phantom* counts predicted rows whose
name is not in the gold; *zero-row pages* counts pages that have gold rows but got none back.

## Layout

```
corpus/   example PDF generator, gold, PII fixture      lanes/    layout, text_llm, vision, text-layer check
gate/     detector, redaction, verifiers, gate           score/    scorer
judge/    typed judge, tasks, policy, backends, CLI      catalog/  example catalog, naive and fixed matcher
bench/    the tables                                     tests/    offline tests
```

See `ARCHITECTURE.md` for the data flow. MIT licensed.

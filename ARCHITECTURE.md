# Architecture

This is example code: it shows the pattern I used, not the production implementation.

Everything below runs on the example corpus of calibration certificates (see `README.md`).

## Data flow

```
                    corpus/generate.py  (fixed seed)
                              |
          +-------------------+--------------------+
          v                   v                    v
   cert_*.pdf            gold/*.csv          pii_fixture.pdf
      |   \                   |                    |
      |    \                  |                    |
      |     v                 |                    v
      |  lanes/text_layer     |              gate/  (fail-closed)
      |  "broken text layer?" |   detect -> redact -> render 200 DPI PNG -> verify
      |     |                 |                |                              |
      v     v                 |                | anything but an explicit     |
  lanes/ (one interface)      |                | pass                         |
   layout | text_llm | vision |                +--------> BLOCK, PNG deleted  |
      |                       |                                               |
      v                       v                                         PASS: cloud-allowed page
  list[Row] ----------> score/  strict, precision / recall, phantom rows,
                              zero-row pages, seconds per page   ----> bench/lanes table

  printed parameter names ---> catalog/matcher  (naive | fixed) ---> bench/matcher table
          |
          v
  judge/ router --> egress policy --refuse--> no call made
          |  allow
          v
    batch of N items per request, C requests at once
          v
    backend: fake | ollama (option-letter log-probabilities) | http (generic endpoint)
          v
    Decision(pick, probabilities, margin = p1 - p2)
          v
    margin >= threshold ? auto-accept : route to a person
```

## Lanes

Every lane is `extract(doc_path) -> list[Row]` with `Row = page, printed_label, value, unit, min, max,
verbatim`.

- **layout**: PyMuPDF word boxes, grouped into lines by vertical position, tail-parsed into
  `name value unit min max`. No model. It assumes one line is one row.
- **text_llm**: the page's text goes in, schema-constrained JSON rows come out. The model name is a
  required environment variable. An answer cut off by the length limit raises an error; it is never
  turned into an empty page.
- **vision**: a 200-DPI PNG of the page goes in, the same JSON comes out.
- **text-layer check**: flags a page whose extracted text contains soft hyphens or zero-width
  characters, or is mostly non-word tokens, so a bench can name the cause.

## Redaction gate

Redact, then an independent check; anything but an explicit pass blocks. The detector is a small set
of patterns and header keywords, with a short keep-list for measurement content. Redaction uses
PyMuPDF `apply_redactions()`, which removes the text, then a PNG is rendered and checked. Only an
explicit pass releases the PNG. The tests plant a fixed set of identifiers and fail if one survives.

## Judge and egress policy

The wire format is `decide(facts, question, choices) -> Decision`. Each task is declared with a data class and each backend with whether it leaves the machine; the
policy refuses a mismatch before anything is sent. A confident error is an auto-accepted pick that is wrong; abstentions
(`none_of_these`, `skip`) are excluded from that count.

## Matcher

Two versions kept side by side. `naive` scores the printed name as written. `fixed` first drops
generic filler words, derived from the catalog itself as the words present in more than a third of
its aliases, then applies a token-set score with a floor. The effect on the bench comes from the data,
not from a hard-coded list.

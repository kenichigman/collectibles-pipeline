# Collectibles pipeline — inventory classification and comps-based pricing

A small pipeline for a comic-book resale inventory: ingest a CSV of
books into SQLite, classify every book, suggest a list price from
comparable sales, and report what needs a human's eye. It is built for
the shape of the problem — thousands of near-unique items, each worth
pricing from evidence rather than from habit.

## The design

- **Two-tier classification.** Tier 1 is a deterministic rule
  classifier: publishing era from the year, a key-issue flag from the
  issue number, grade band, and quantity. It always runs and always
  answers. Tier 2 is an optional local LLM, reached through an
  Ollama-compatible HTTP endpoint, that re-checks the rule result.
  Model output is untrusted input: it must name one of the known
  classes in JSON, and any failure — timeout, bad JSON, an invented
  label — falls back to the rule result. The tier is a second opinion,
  never a dependency, and it is off unless explicitly enabled.
- **Comps-median pricing.** The price evidence for a book is the set of
  comparable sales: same title and issue, same grade band, sold within
  a year of the newest comp on file. The suggested list price is the
  median of that set with a haircut (default 10%) — the median is what
  copies actually sold for, and a listing is an ask, not a sale.
- **Confidence is a property of the evidence, not the price.** Five or
  more recent comps is high confidence; three is medium; one or two is
  low; none means the book stays unpriced and goes on the report's
  human-review list. A price the data can't support is worse than no
  price.
- **SQLite is the whole store.** One file, a documented schema, no
  server. The database is the interface between stages: ingest,
  classify, price, and the dashboard each read and write the same
  tables, so any stage can be re-run or replaced independently.
- **Adapters at the edges.** Comps arrive through a loader into a
  `comps` table with a fixed shape. This edition ships a CSV loader; a
  marketplace API client would fill the same table through the same
  columns, and nothing downstream would change. There are no live API
  calls and no credentials anywhere in this repo.

## Layout

```
pipeline/       the core package (standard library only)
  db.py         schema, CSV ingest, normalized title/issue matching
  classify.py   tier-1 rules + tier-2 dispatch
  llm.py        optional local-LLM client (Ollama-compatible HTTP)
  pricing.py    comp selection, median + haircut, confidence flags
  report.py     plain-text summary report
  __main__.py   CLI: ingest | classify | price | report
dashboard.py    optional Streamlit view over the same database
fixtures/       sample inventory (25 rows) and sample comps (42 rows);
                every figure in them is invented sample data
tests/          assert-based end-to-end tests, no framework required
run_tests.sh    the tests plus a full CLI pass over the fixtures
```

## Running it

```bash
python3 -m pipeline --db pipeline.db ingest \
    --inventory fixtures/sample_inventory.csv \
    --comps fixtures/sample_comps.csv
python3 -m pipeline --db pipeline.db classify
python3 -m pipeline --db pipeline.db price            # --haircut 0.10
python3 -m pipeline --db pipeline.db report
```

To enable the LLM second tier, point it at a local endpoint and pass
the flag; with either variable unset, classification is rules-only.

```bash
PIPELINE_LLM_URL=http://localhost:11434 \
PIPELINE_LLM_MODEL=llama3.1:8b \
python3 -m pipeline --db pipeline.db classify --llm
```

The dashboard is the only piece with a third-party dependency:

```bash
pip install streamlit
PIPELINE_DB=pipeline.db streamlit run dashboard.py
```

Tests: `./run_tests.sh` (Python 3.10+, standard library only).

## Inventory and comps formats

Inventory CSV: `title, issue, publisher, year, grade, quantity,
cost_basis` (cost per copy). Comps CSV: `title, issue, grade,
sold_price, sold_date` (ISO dates). Lines starting with `#` are
comments and are skipped, which is how the sample files carry their
"this data is invented" headers.

## Status

This is a reference implementation, rebuilt clean from a working
private system (an earlier design that paired the same two-tier
classification with a marketplace-API pricing feed and a dashboard).
The rebuild keeps the design and replaces the data: the original's
real inventory, sales history, and accounts are not included, and the
fixtures are invented sample data marked as such. What is here is
runnable end to end and tested; what is deliberately not here is any
live marketplace integration — the adapter seam is the CSV loader,
documented above.

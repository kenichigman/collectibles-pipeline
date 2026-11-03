#!/usr/bin/env bash
# Runs the assert-based test suite plus an end-to-end CLI pass over the
# shipped fixtures. Standard library only; no installs.
set -euo pipefail
cd "$(dirname "$0")"

python3 tests/test_pipeline.py

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 -m pipeline --db "$TMP/demo.db" ingest \
    --inventory fixtures/sample_inventory.csv \
    --comps fixtures/sample_comps.csv
python3 -m pipeline --db "$TMP/demo.db" classify
python3 -m pipeline --db "$TMP/demo.db" price
python3 -m pipeline --db "$TMP/demo.db" report

echo "ALL TESTS PASSED"

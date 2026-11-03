"""SQLite storage: schema, CSV ingest, and small query helpers.

Schema
------
inventory(
    id INTEGER PRIMARY KEY,
    title TEXT, issue TEXT, publisher TEXT,
    year INTEGER, grade REAL,
    quantity INTEGER, cost_basis REAL,       -- per-copy cost
    era TEXT, is_key INTEGER, class TEXT,    -- filled by classify
    suggested_price REAL, price_confidence TEXT,  -- filled by price
    price_basis TEXT                          -- how the price was derived
)
comps(
    id INTEGER PRIMARY KEY,
    title TEXT, issue TEXT, grade REAL,
    sold_price REAL, sold_date TEXT          -- ISO date, YYYY-MM-DD
)

Titles and issues are matched on a normalized key (lowercased, leading
'#' stripped from the issue, whitespace collapsed) so 'X-Men' / 'x-men '
and '#1' / '1' are the same book.
"""

import csv
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    issue TEXT NOT NULL,
    publisher TEXT,
    year INTEGER,
    grade REAL,
    quantity INTEGER DEFAULT 1,
    cost_basis REAL,
    era TEXT,
    is_key INTEGER DEFAULT 0,
    class TEXT,
    suggested_price REAL,
    price_confidence TEXT,
    price_basis TEXT
);
CREATE TABLE IF NOT EXISTS comps (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    issue TEXT NOT NULL,
    grade REAL,
    sold_price REAL NOT NULL,
    sold_date TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comps_key ON comps (title, issue);
"""


def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def norm_title(title):
    return " ".join((title or "").strip().lower().split())


def norm_issue(issue):
    return (issue or "").strip().lstrip("#").strip().lower()


def _rows(path):
    """Yield DictReader rows from a CSV, skipping '#' comment lines."""
    with open(path, newline="", encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.lstrip().startswith("#")]
    yield from csv.DictReader(lines)


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    f = _float(value)
    return int(f) if f is not None else None


def ingest_inventory(db, path):
    n = 0
    for r in _rows(path):
        db.execute(
            "INSERT INTO inventory (title, issue, publisher, year, grade,"
            " quantity, cost_basis) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                r["title"].strip(),
                norm_issue(r["issue"]),
                (r.get("publisher") or "").strip() or None,
                _int(r.get("year")),
                _float(r.get("grade")),
                _int(r.get("quantity")) or 1,
                _float(r.get("cost_basis")),
            ),
        )
        n += 1
    db.commit()
    return n


def ingest_comps(db, path):
    n = 0
    for r in _rows(path):
        db.execute(
            "INSERT INTO comps (title, issue, grade, sold_price, sold_date)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                norm_title(r["title"]),
                norm_issue(r["issue"]),
                _float(r.get("grade")),
                _float(r["sold_price"]),
                r["sold_date"].strip(),
            ),
        )
        n += 1
    db.commit()
    return n


def inventory_rows(db):
    return db.execute("SELECT * FROM inventory ORDER BY id").fetchall()


def latest_comp_date(db):
    row = db.execute("SELECT MAX(sold_date) AS d FROM comps").fetchone()
    return row["d"]


def comps_for(db, title, issue):
    return db.execute(
        "SELECT * FROM comps WHERE title = ? AND issue = ?"
        " ORDER BY sold_date DESC",
        (norm_title(title), norm_issue(issue)),
    ).fetchall()

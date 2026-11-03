"""Comparable-sales pricing.

For each inventory book, the comp set is: same title + issue, same grade
band (see classify.grade_band), sold within RECENT_DAYS of the newest
comp in the database. The window is dataset-relative on purpose — it
behaves the same on a live feed and on a frozen sample file.

    suggested_price = median(comp prices) * (1 - HAIRCUT)

HAIRCUT (default 0.10) lists a book slightly under the recent median:
the median is what the last copies actually sold for, and a listing is
an ask, not a sale. It is a flag, not a constant buried in the math.

Confidence is a function of evidence, not of the price:
    high    >= 5 comps and the newest is <= 180 days old
    medium  >= 3 comps
    low     1-2 comps
    none    no comps in band/window — the book stays unpriced

Pricing feeds off a comps table. In this edition the comps arrive as a
CSV; the loader is the adapter seam — a marketplace API client would
fill the same table through the same columns and nothing downstream
would change.
"""

import statistics
from datetime import date

from .classify import grade_band
from .db import comps_for, latest_comp_date

RECENT_DAYS = 365
HIGH_MIN_COMPS = 5
HIGH_MAX_AGE_DAYS = 180
MEDIUM_MIN_COMPS = 3
DEFAULT_HAIRCUT = 0.10


def _days(a, b):
    return (date.fromisoformat(a) - date.fromisoformat(b)).days


def confidence_for(comp_dates, anchor):
    n = len(comp_dates)
    if n == 0:
        return "none"
    newest_age = _days(anchor, max(comp_dates))
    if n >= HIGH_MIN_COMPS and newest_age <= HIGH_MAX_AGE_DAYS:
        return "high"
    if n >= MEDIUM_MIN_COMPS:
        return "medium"
    return "low"


def price_all(db, haircut=DEFAULT_HAIRCUT):
    anchor = latest_comp_date(db)
    stats = {"priced": 0, "unpriced": 0, "by_confidence": {}}
    if anchor is None:
        return stats
    for row in db.execute("SELECT * FROM inventory").fetchall():
        band = grade_band(row["grade"])
        comps = [
            c
            for c in comps_for(db, row["title"], row["issue"])
            if grade_band(c["grade"]) == band
            and _days(anchor, c["sold_date"]) <= RECENT_DAYS
        ]
        conf = confidence_for([c["sold_date"] for c in comps], anchor)
        if comps:
            median = statistics.median(c["sold_price"] for c in comps)
            price = round(median * (1 - haircut), 2)
            basis = (
                f"median of {len(comps)} comp(s) in {band} band, "
                f"haircut {haircut:.0%}"
            )
            stats["priced"] += 1
        else:
            price, basis = None, "no comps in grade band within window"
            stats["unpriced"] += 1
        stats["by_confidence"][conf] = stats["by_confidence"].get(conf, 0) + 1
        db.execute(
            "UPDATE inventory SET suggested_price = ?, price_confidence = ?,"
            " price_basis = ? WHERE id = ?",
            (price, conf, basis, row["id"]),
        )
    db.commit()
    return stats

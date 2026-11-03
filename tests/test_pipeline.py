"""End-to-end tests: plain asserts, no test framework required.

    python3 tests/test_pipeline.py

Covers the unit rules, a small deterministic ingest -> classify -> price
run with an exactly known median, and a smoke run over the shipped
fixtures.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline import classify as C
from pipeline import db as DB
from pipeline import pricing, report

ROOT = os.path.join(os.path.dirname(__file__), "..")
passed = []


def check(name, cond):
    assert cond, f"FAILED: {name}"
    passed.append(name)


# --- unit rules ---------------------------------------------------------
check("era golden", C.era_of(1950) == "golden_age")
check("era silver", C.era_of(1963) == "silver_age")
check("era bronze", C.era_of(1974) == "bronze_age")
check("era modern", C.era_of(2003) == "modern")
check("era unknown", C.era_of(None) == "unknown")
check("band high", C.grade_band(9.2) == "high")
check("band mid", C.grade_band(8.5) == "mid")
check("band low", C.grade_band(5.5) == "low")
check("key #1", C.is_key_issue("#1") and C.is_key_issue("1"))
check("not key #7", not C.is_key_issue("7"))
check("key high grade", C.rule_classify("silver_age", 1, 8.5, 1)
      == "key_high_grade")
check("bulk", C.rule_classify("modern", 0, 5.5, 12) == "bulk")

# --- deterministic mini run ---------------------------------------------
tmp = tempfile.mkdtemp()
inv = os.path.join(tmp, "inv.csv")
comps = os.path.join(tmp, "comps.csv")
with open(inv, "w") as f:
    f.write("# SAMPLE DATA: invented.\n")
    f.write("title,issue,publisher,year,grade,quantity,cost_basis\n")
    f.write("X-Men,1,Marvel,1963,8.5,1,850.00\n")
    f.write("Bulk Heroes,7,Example,1992,5.5,12,4.00\n")
    f.write("Mystery Comic,3,Example,2001,9.0,1,10.00\n")
with open(comps, "w") as f:
    f.write("# SAMPLE DATA: invented.\n")
    f.write("title,issue,grade,sold_price,sold_date\n")
    for price, day in [(100, "2026-10-20"), (120, "2026-09-01"),
                       (110, "2026-08-01"), (130, "2026-07-01"),
                       (90, "2026-06-01")]:
        f.write(f"X-Men,1,8.0,{price}.00,{day}\n")

db = DB.connect(os.path.join(tmp, "t.db"))
check("mini ingest counts",
      DB.ingest_inventory(db, inv) == 3 and DB.ingest_comps(db, comps) == 5)
C.classify_all(db)
pricing.price_all(db)  # default haircut 0.10

rows = {r["title"]: r for r in DB.inventory_rows(db)}
xmen = rows["X-Men"]
check("mini class", xmen["class"] == "key_high_grade")
check("mini median price", xmen["suggested_price"] == 99.00)  # 110 * 0.9
check("mini confidence high", xmen["price_confidence"] == "high")
check("mini bulk class", rows["Bulk Heroes"]["class"] == "bulk")
myst = rows["Mystery Comic"]
check("mini unpriced", myst["suggested_price"] is None
      and myst["price_confidence"] == "none")
check("report renders", "By class:" in report.render_report(db))

# --- fixtures smoke -------------------------------------------------------
db2 = DB.connect(os.path.join(tmp, "f.db"))
n_inv = DB.ingest_inventory(db2, os.path.join(ROOT, "fixtures",
                                              "sample_inventory.csv"))
n_comps = DB.ingest_comps(db2, os.path.join(ROOT, "fixtures",
                                            "sample_comps.csv"))
check("fixture counts", n_inv == 25 and n_comps == 42)
C.classify_all(db2)
stats = pricing.price_all(db2)
rows2 = {(r["title"], r["issue"]): r for r in DB.inventory_rows(db2)}
check("fixture key class",
      rows2[("X-Men", "1")]["class"] == "key_high_grade")
check("fixture bulk class", rows2[("Bone", "7")]["class"] == "bulk")
wd = rows2[("Walking Dead", "1")]
check("fixture high confidence",
      wd["suggested_price"] is not None
      and wd["price_confidence"] == "high")
dd = rows2[("Daredevil", "1")]
check("stale comps excluded by window",
      dd["suggested_price"] is None and dd["price_confidence"] == "none")
check("some priced, some not", stats["priced"] > 0 and stats["unpriced"] > 0)

print(f"test_pipeline: {len(passed)} checks passed")
for name in passed:
    print(f"  ok - {name}")

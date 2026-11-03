"""Two-tier classification.

Tier 1 (always on) is a deterministic rule classifier: publishing era
from the year, a key-issue flag from the issue number, a grade band, and
a bulk flag from quantity. Rules are ordered; the first match wins, and
every book gets exactly one class.

Tier 2 (optional, off by default) asks a local LLM, through an
Ollama-compatible HTTP endpoint, to re-check the rule result. It only
ever runs when explicitly enabled (see llm.py), and any failure falls
back to the tier-1 result. The LLM never invents a label: answers
outside the known class list are discarded.
"""

from .llm import llm_classify

CLASSES = (
    "key_high_grade",
    "key_issue",
    "vintage_high_grade",
    "vintage",
    "bulk",
    "back_issue",
)


def era_of(year):
    if year is None:
        return "unknown"
    if year < 1956:
        return "golden_age"
    if year < 1970:
        return "silver_age"
    if year < 1985:
        return "bronze_age"
    if year < 1992:
        return "copper_age"
    return "modern"


def grade_band(grade):
    """Shared with pricing: comps only count inside the same band."""
    if grade is None:
        return "ungraded"
    if grade >= 9.0:
        return "high"
    if grade >= 6.0:
        return "mid"
    return "low"


def is_key_issue(issue):
    """Heuristic: a first issue is a key. (Deliberately narrow — a real
    key list is data, not code, and belongs in a table of its own.)"""
    return (issue or "").strip().lstrip("#").strip() == "1"


def rule_classify(era, key, grade, quantity):
    band = grade_band(grade)
    if key and band in ("high", "mid") and (grade or 0) >= 8.0:
        return "key_high_grade"
    if key:
        return "key_issue"
    if era in ("golden_age", "silver_age") and band == "high":
        return "vintage_high_grade"
    if era in ("golden_age", "silver_age", "bronze_age"):
        return "vintage"
    if (quantity or 1) >= 10 and band == "low":
        return "bulk"
    return "back_issue"


def classify_all(db, use_llm=False):
    counts = {}
    for row in db.execute("SELECT * FROM inventory").fetchall():
        era = era_of(row["year"])
        key = 1 if is_key_issue(row["issue"]) else 0
        cls = rule_classify(era, key, row["grade"], row["quantity"])
        if use_llm:
            llm_cls = llm_classify(
                row["title"], row["issue"], row["publisher"],
                row["year"], row["grade"], CLASSES,
            )
            if llm_cls in CLASSES:
                cls = llm_cls
        db.execute(
            "UPDATE inventory SET era = ?, is_key = ?, class = ? WHERE id = ?",
            (era, key, cls, row["id"]),
        )
        counts[cls] = counts.get(cls, 0) + 1
    db.commit()
    return counts

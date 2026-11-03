"""Streamlit dashboard over the pipeline database.

    PIPELINE_DB=pipeline.db streamlit run dashboard.py

Streamlit is the project's only third-party dependency, and only for
this file: the ingest/classify/price core runs on the standard library
alone. If streamlit is not installed, this prints how to install it and
exits — it never takes the pipeline down with it.
"""

import os
import sqlite3
import sys

try:
    import streamlit as st
except ImportError:
    sys.exit("streamlit is not installed. Install it with:\n"
             "    pip install streamlit\n"
             "The pipeline core (python -m pipeline ...) does not need it.")

DB_PATH = os.environ.get("PIPELINE_DB", "pipeline.db")


def query(sql, args=()):
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in db.execute(sql, args)]
    finally:
        db.close()


st.set_page_config(page_title="Collectibles pipeline", layout="wide")
st.title("Collectibles inventory pipeline")

summary = query(
    "SELECT COUNT(*) AS titles, SUM(quantity) AS copies,"
    " SUM(suggested_price * quantity) AS value,"
    " SUM(cost_basis * quantity) AS cost FROM inventory"
)[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Titles", summary["titles"] or 0)
c2.metric("Copies", summary["copies"] or 0)
c3.metric("Suggested value", f"${summary['value'] or 0:,.2f}")
c4.metric("Cost basis", f"${summary['cost'] or 0:,.2f}")

st.subheader("By class")
st.dataframe(
    query(
        "SELECT class, COUNT(*) AS titles, SUM(quantity) AS copies"
        " FROM inventory GROUP BY class ORDER BY titles DESC"
    ),
    use_container_width=True,
)

st.subheader("Inventory and suggested prices")
st.dataframe(
    query(
        "SELECT title, issue, publisher, year, grade, quantity, class,"
        " suggested_price, price_confidence, price_basis"
        " FROM inventory ORDER BY title, CAST(issue AS INTEGER)"
    ),
    use_container_width=True,
)

st.subheader("Needs a human: low-confidence and unpriced")
st.dataframe(
    query(
        "SELECT title, issue, grade, quantity, cost_basis,"
        " price_confidence FROM inventory"
        " WHERE price_confidence IN ('low', 'none')"
        " OR price_confidence IS NULL ORDER BY title"
    ),
    use_container_width=True,
)

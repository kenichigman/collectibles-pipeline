"""Plain-text summary report over a priced inventory."""


def render_report(db):
    total = db.execute("SELECT COUNT(*) AS n FROM inventory").fetchone()["n"]
    lines = [f"Inventory: {total} line item(s)", "", "By class:"]
    for row in db.execute(
        "SELECT COALESCE(class, '(unclassified)') AS c, COUNT(*) AS n,"
        " SUM(quantity) AS q FROM inventory GROUP BY c ORDER BY n DESC"
    ):
        lines.append(f"  {row['c']:<20} {row['n']:>3} title(s), {row['q']} copies")

    lines += ["", "Pricing:"]
    for row in db.execute(
        "SELECT COALESCE(price_confidence, '(not priced)') AS c,"
        " COUNT(*) AS n FROM inventory GROUP BY c ORDER BY n DESC"
    ):
        lines.append(f"  confidence {row['c']:<8} {row['n']:>3}")

    agg = db.execute(
        "SELECT SUM(suggested_price * quantity) AS v,"
        " SUM(cost_basis * quantity) AS cost FROM inventory"
        " WHERE suggested_price IS NOT NULL"
    ).fetchone()
    if agg["v"] is not None:
        lines.append(
            f"  suggested value ${agg['v']:,.2f} on cost basis"
            f" ${agg['cost'] or 0:,.2f}"
        )

    low = db.execute(
        "SELECT title, issue, grade, price_confidence FROM inventory"
        " WHERE price_confidence IN ('low', 'none')"
        " OR price_confidence IS NULL ORDER BY title"
    ).fetchall()
    lines += ["", f"Low-confidence / unpriced ({len(low)}):"]
    for row in low:
        lines.append(
            f"  {row['title']} #{row['issue']} (grade {row['grade']})"
            f" — {row['price_confidence'] or 'not priced'}"
        )
    return "\n".join(lines)

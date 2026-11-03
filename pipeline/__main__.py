"""CLI: python -m pipeline [--db PATH] <ingest|classify|price|report>

    ingest    --inventory inv.csv [--comps comps.csv]
    classify  [--llm]     tier 2 only if PIPELINE_LLM_* are set (see llm.py)
    price     [--haircut 0.10]
    report
"""

import argparse

from . import classify as classify_mod
from . import db as db_mod
from . import pricing, report


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline")
    ap.add_argument("--db", default="pipeline.db", help="SQLite path")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest")
    p.add_argument("--inventory")
    p.add_argument("--comps")

    p = sub.add_parser("classify")
    p.add_argument(
        "--llm",
        action="store_true",
        help="enable the optional local-LLM second tier",
    )

    p = sub.add_parser("price")
    p.add_argument("--haircut", type=float, default=pricing.DEFAULT_HAIRCUT)

    sub.add_parser("report")
    args = ap.parse_args(argv)

    db = db_mod.connect(args.db)
    if args.cmd == "ingest":
        if args.inventory:
            print(f"ingested {db_mod.ingest_inventory(db, args.inventory)}"
                  " inventory row(s)")
        if args.comps:
            print(f"ingested {db_mod.ingest_comps(db, args.comps)} comp(s)")
    elif args.cmd == "classify":
        counts = classify_mod.classify_all(db, use_llm=args.llm)
        for cls, n in sorted(counts.items()):
            print(f"  {cls:<20} {n}")
    elif args.cmd == "price":
        stats = pricing.price_all(db, haircut=args.haircut)
        print(f"priced {stats['priced']}, unpriced {stats['unpriced']}")
        for conf, n in sorted(stats["by_confidence"].items()):
            print(f"  confidence {conf:<8} {n}")
    elif args.cmd == "report":
        print(report.render_report(db))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
